import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import fsgui.spikegadgets.action.shortcut
import fsgui.spikegadgets.action
import fsgui.spikegadgets.action
import functools
import operator
import time

class SimpleDigitalPulseWaveActionType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        name='Simple digital pulsetrain'
        super().__init__(
            type_id=type_id,
            node_class='action',
            name=name,
            datatype=None,
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'filter_id': None,
                'pulseLength': 20,
                'nPulses': 10,
                'sequencePeriod': 100,
                'primaryBit': 1,
                'functNum': 20,
            }
        )

        self.network_location = network_location

    def get_gui_config(self):
        return [
            {
                'type': 'checkbox',
                'label': 'laser enabled',
                'name': 'enabled',
                'checked': 'enable',
                'unchecked': 'disable',
            },
        ]

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
                'label': 'Filter',
                'name': 'filter_id',
                'type': 'node:tree',
                'default': config['filter_id'],
                'tooltip': 'Filter on which to trigger our action',
            },
            {
                'label': 'Pulse length',
                'name': 'pulseLength',
                'type': 'integer',
                'lower': 1,
                'upper': 500,
                'default': config['pulseLength'],
                'units': 'ms',
                'tooltip': 'Length in milliseconds of each pulse in pulse sequence.'
            },
            {
                'label': '# of Pulses',
                'name': 'nPulses',
                'type': 'integer',
                'lower': 0,
                'upper': 10000,
                'default': config['nPulses'],
                'tooltip': 'Number of pulses in pulse sequence.'
            },
            {
                'label': 'Period',
                'name': 'sequencePeriod',
                'type': 'integer',
                'lower': 1,
                'upper': 5000,
                'decimals': 0,
                'default': config['sequencePeriod'],
                'units': 'ms',
                'tooltip': 'Period of pulses in pulse sequence.',
            },
            {
                'label': 'Primary pin',
                'name': 'primaryBit',
                'type': 'integer',
                'lower': 1,
                'upper': 64,
                'default': config['primaryBit'],
                'tooltip': 'Output pin (range 1 - 64) to stimulate. For biphasic triggering, this is the first pin '
                           'triggered.', 
            },
            {
                'label': 'Function number',
                'name': 'functNum',
                'type': 'integer',
                'lower': 0,
                'upper': 32,
                'default': config['functNum'],
                'tooltip': 'StateScript function number to run.',
            },
        ]
    
    def build(self, config, address_map):
        train_length = config['nPulses'] * config['sequencePeriod']

        # send the script
        consumer = trodesnetwork.ServiceConsumer('statescript.service', server_address = f'{self.network_location.address}:{self.network_location.port}')
        consumer.request({
            'command': fsgui.spikegadgets.action.generate_statescript(
                function_num=config['functNum'],
                pre_delay=0,
                n_pulses=config['nPulses'],
                n_trains=1,
                train_interval=train_length,
                sequence_period=config['sequencePeriod'],
                primary_stim_pin=config['primaryBit'],
                pulse_length=config['pulseLength']
            ),
        })

        return fsgui.spikegadgets.action.build_shortcut_command(
            pipe_map=address_map,
            filter_tree=config['filter_id'],
            network_location=self.network_location,
            lockout_time=train_length,
            on_funct_num=config['functNum'],
            off_funct_num=config['functNum'] + 1,
            abort_funct_num=config['functNum'] + 1,
        )
