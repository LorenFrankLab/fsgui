import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.network
import fsgui.spikegadgets.trodes
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import logging
import json
import numpy as np
import time


class SpikesDataType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        self.network_location = network_location
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='Trodes Spikes',
            datatype='spikes',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Trodes Spikes',
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
        ]

    def build(self, config, addr_map):
        try:
            # check connection to fail during build rather than process runtime
            trodesnetwork.SourceSubscriber('source.waveforms', server_address = f'{self.network_location.address}:{self.network_location.port}')
        except Exception:
            raise ValueError('Could not connect to Trodes spikes')

        def setup(reporter, data):
            data['spikes_sub'] = trodesnetwork.SourceSubscriber('source.waveforms', server_address = f'{self.network_location.address}:{self.network_location.port}')

        def workload(connection, publisher, reporter, data):
            spikes_data = data['spikes_sub'].receive(timeout=50)
            if spikes_data is not None:
                publisher.send(spikes_data)
       
        return fsgui.process.build_process_object(setup, workload)