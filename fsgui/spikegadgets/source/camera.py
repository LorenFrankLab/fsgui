import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import fsgui.network
import time
 
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
        try:
            trodesnetwork.SourceSubscriber('source.position', server_address = f'{self.network_location.address}:{self.network_location.port}')
        except Exception:
            raise ValueError('Could not connect to Trodes camera')

        def setup(logging, data):
            data['camera_sub'] = trodesnetwork.SourceSubscriber('source.position', server_address = f'{self.network_location.address}:{self.network_location.port}')
            data['receive_none_counter'] = 0

        def workload(logging, messages, publisher, reporter, data):
            camera_data = data['camera_sub'].receive(timeout=50)
            if camera_data is None:
                data['receive_none_counter'] += 1
                if data['receive_none_counter'] > 40 and data['receive_none_counter'] % 40 == 0:
                    logging.info(f'Camera source has not received any camera data from Trodes in a while...')
            if camera_data is not None:
                data['receive_none_counter'] = 0
                publisher.send(camera_data)

        return fsgui.process.build_process_object(setup, workload)
        