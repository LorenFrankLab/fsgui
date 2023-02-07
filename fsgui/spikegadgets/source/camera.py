import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging

 
class CameraDataType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='Trodes Camera',
            datatype='point2d',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Trodes Camera',
            }
        )

        self.network_location = network_location

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
        ]
    
    def build(self, config, addr_map):
        # import fsgui.spikegadgets.trodesnetwork as trodesnetwork
        # trodesnetwork.SourceSubscriber('source.position', server_address = f'{self.network_location.address}:{self.network_location.port}')
        return CameraSource(network_location = self.network_location)

class CameraSource:
    def __init__(self, network_location):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        import time

        def setup(data):
            import fsgui.network
            import fsgui.spikegadgets.trodesnetwork as trodesnetwork
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

            # set up the actual subscriber
            data['camera_sub'] = trodesnetwork.SourceSubscriber('source.position', server_address = f'{network_location.address}:{network_location.port}')

        def workload(data):
            camera_data = data['camera_sub'].receive(timeout=50)
            if camera_data is not None:
                x = camera_data['x']
                y = camera_data['y']
                data['publisher'].send(f'{x},{y}')
        
        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()

        self.pub_address = pipe_recv.recv()
