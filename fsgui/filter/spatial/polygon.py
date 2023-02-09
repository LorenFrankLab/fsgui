import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node
import json
import shapely


class GeometryFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name = 'Geometry filter'

        super().__init__(
            type_id=type_id,
            node_class='filter',
            name=name,
            datatype='bool',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'source_id': None,
                'filename': '',
                'cameraWidth': 1000,
                'cameraHeight': 1000,
            }
        )

    def write_template(self, config = None):
        if config is None:
            config = self.default()
        return [
            {
                'name': 'type_id',
                'type': 'hidden',
                'default': config['type_id'],
            },
            {
                'name': 'instance_id',
                'type': 'hidden',
                'default': config['instance_id'],
            },
            {
                'label': 'Nickname',
                'name': 'nickname',
                'type': 'string',
                'default': config['nickname'],
                'tooltip': 'This is the name the source is displayed as in menus.',
            },
            {
                'label': 'Source',
                'name': 'source_id',
                'type': 'node:point2d',
                'default': config['source_id'],
                'tooltip': 'Source to receive spatial data from',
            },
            {
                'label': 'Geometry file',
                'name': 'filename',
                'type': 'geometry',
                'default': config['filename'],
            },
            {
                'label': 'Camera width (X)',
                'name': 'cameraWidth',
                'type': 'integer',
                'lower': 0,
                'upper': 10000,
                'default': config['cameraWidth'],
                'units': 'pixels',
            },
            {
                'label': 'Camera height (Y)',
                'name': 'cameraHeight',
                'type': 'integer',
                'lower': 0,
                'upper': 10000,
                'default': config['cameraHeight'],
                'units': 'pixels',
            },
       ]

    def build(self, config, addr_map):
        source_id = config['source_id']
        pub_address = addr_map[source_id]
        
        import fsgui.geometry

        reader = fsgui.geometry.TrackGeometryFileReader()
        geometry_file = reader.read_file(config['filename'])

        width = config['cameraWidth']
        height = config['cameraHeight']

        poly = shapely.geometry.Polygon(
            # rescale from geometry file
            [(x * width, y * height) for x, y in geometry_file.get_inclusion_zone[0].polygon.nodes]
        )

        return GeometryFilterProcess(pub_address, poly)

class GeometryFilterProcess:
    def __init__(self, source_pub_address, shapely_polygon):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(source_pub_address)
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())
            data['filter_model'] = PolygonFilter(shapely_polygon)

        def workload(data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                x, y = tuple(map(float, item.split(',')))
                triggered = data['filter_model'].point_in_polygon(x, y)
                data['publisher'].send(f'{triggered}')

        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()
        self.pub_address = pipe_recv.recv()
    
class PolygonFilter:
    def __init__(self, shapely_polygon):
        self._polygon = shapely_polygon
    
    def point_in_polygon(self, x, y):
        point = shapely.geometry.Point(x, y)
        return self._polygon.contains(point)
