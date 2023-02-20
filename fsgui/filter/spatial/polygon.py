import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node
import json
import shapely
import fsgui.geometry

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
                'trackgeometry': {'filename': '', 'zone_id': None},
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
                'name': 'trackgeometry',
                'type': 'geometry',
                'default': config['trackgeometry'],
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
        pub_address = addr_map[config['source_id']]

        geometry_file = fsgui.geometry.TrackGeometryFileReader().read_file(config['trackgeometry']['filename'])

        shapely_polygon = shapely.geometry.Polygon(
            # rescale from geometry file
            [(x * config['cameraWidth'], y * config['cameraHeight']) for x, y in geometry_file['zone'][config['trackgeometry']['zone_id']]]
        )

        def setup(reporter, data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(pub_address)
            data['filter_model'] = PolygonFilter(shapely_polygon)

        def workload(reporter, publisher, data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                x, y = tuple(map(float, item.split(',')))
                triggered = data['filter_model'].point_in_polygon(x, y)
                publisher.send(f'{triggered}')

        return fsgui.process.build_process_object(setup, workload)
    
class PolygonFilter:
    def __init__(self, shapely_polygon):
        self._polygon = shapely_polygon
    
    def point_in_polygon(self, x, y):
        point = shapely.geometry.Point(x, y)
        return self._polygon.contains(point)
