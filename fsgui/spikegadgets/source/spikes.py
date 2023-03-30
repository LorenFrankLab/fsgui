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
        )

    def write_template(self, config = None):
        config = config if config is not None else {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'voltage_scaling_factor': 0.195,
        }

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
                'label': 'Voltage scaling factor',
                'name': 'voltage_scaling_factor',
                'type': 'double',
                'lower': 0,
                'upper': 10000,
                'decimals': 3,
                'default': config['voltage_scaling_factor'],
                'tooltip': 'This is multiplied by every spike value.',
                'live_editable': True,
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
            if connection.pipe_poll(timeout = 0):
                msg_tag, msg_data = connection.pipe_recv()
                if msg_tag == 'update':
                    msg_varname, msg_value = msg_data
                    config[msg_varname] = msg_value

            spikes_data = data['spikes_sub'].receive(timeout=50)
            if spikes_data is not None:
                spikes_data['samples'] = (np.array(spikes_data['samples']) * config['voltage_scaling_factor']).tolist()
                publisher.send(spikes_data)
       
        return fsgui.process.build_process_object(setup, workload)