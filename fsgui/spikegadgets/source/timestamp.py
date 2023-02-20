import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging
import json
import time
import fsgui.network
import fsgui.spikegadgets.trodesnetwork as trodesnetwork

class TimestampDataType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        name='Trodes timestamps'
        super().__init__(
            type_id=type_id,
            node_class='source',
            name=name,
            datatype='timestamp',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
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
            trodesnetwork.SourceSubscriber('source.lfp', server_address = f'{self.network_location.address}:{self.network_location.port}')
        except Exception:
            raise ValueError('Could not connect to Trodes source')
 
        def setup(reporter, data):
            data['sub'] = trodesnetwork.SourceSubscriber('source.lfp', server_address = f'{self.network_location.address}:{self.network_location.port}')

        def workload(reporter, publisher, data):
            timestamp_data = data['sub'].receive(timeout=50)
            if timestamp_data is not None:
                hardware_ts = timestamp_data['localTimestamp']
                publisher.send(f'{hardware_ts}')
        
        return fsgui.process.build_process_object(setup, workload)
