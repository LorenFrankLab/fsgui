import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.network
import fsgui.spikegadgets.trodes
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import json
import time

class LFPDataType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='Trodes LFP',
            datatype='float',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Trodes LFP',
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
            # check connection to fail during build rather than process runtime
            trodesnetwork.SourceSubscriber('source.lfp', server_address = f'{self.network_location.address}:{self.network_location.port}')
        except Exception:
            raise ValueError('Could not connect to trodes source')
        
        def setup(logging, data):
            data['lfp_sub'] = trodesnetwork.SourceSubscriber('source.lfp', server_address = f'{self.network_location.address}:{self.network_location.port}')
            data['receive_none_counter'] = 0

        def workload(logging, publisher, reporter, data):
            lfp_data = data['lfp_sub'].receive(timeout=50)
            if lfp_data is None:
                data['receive_none_counter'] += 1
                if data['receive_none_counter'] > 40 and data['receive_none_counter'] % 40 == 0:
                    logging.info(f'LFP source has not received any LFP data from Trodes in a while...')
            else:
                data['receive_none_counter'] = 0
                publisher.send(lfp_data)
        
        return fsgui.process.build_process_object(setup, workload)
