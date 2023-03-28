import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import fsgui.spikegadgets.action.shortcut
import functools
import operator
import time

class DigitalPulseWaveActionType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        super().__init__(
            type_id=type_id,
            node_class='action',
            name='Digital Pulsetrain',
            datatype=None,
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Digital Pulsetrain',
                'filter_id': None,
                'pulseLength': 1,
                'nPulses': 1,
                'preDelay': 0,
                'sequencePeriod': 100,
                'sequenceFrequency': 10,
                'autoSettle': True,
                'nOutputTrains': 1,
                'trainInterval': 1000,
                'primaryBit': 1,
                'biphasic': False,
                'secondaryBit': 1,
                'lockout_time': 0,
                'functNum': 0,
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
            {
                'type': 'button',
                'label': 'abort',
                'name': 'abort',
                'pressed': 'abort',
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
                'label': 'Pre Delay',
                'name': 'preDelay',
                'type': 'integer',
                'lower': 0,
                'upper': 1000,
                'default': config['preDelay'],
                'units': 'ms',
                'tooltip': 'Time before first pulse',
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
                'label': 'Number of output trains',
                'name': 'nOutputTrains',
                'type': 'integer',
                'lower': 0,
                'upper': 200,
                'default': config['nOutputTrains'],
                'tooltip': 'Number of output sequences to trigger before returning; Set to 0 for continuous trains',
                'special': 'Inf.',
            },
            {
                'label': 'Inter-train Interval',
                'name': 'trainInterval',
                'type': 'integer',
                'lower': 100,
                'upper': 60000,
                'default': config['trainInterval'],
                'units': 'ms',
                'tooltip': 'Time in milliseconds from the onset of one pulse/pulse sequence to the onset of the next.',
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
                'label': 'Lockout time',
                'name': 'lockout_time',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['lockout_time'],
                'tooltip': 'Time in milliseconds to wait before triggering again.',
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
        # send the script
        consumer = trodesnetwork.ServiceConsumer('statescript.service', server_address = f'{self.network_location.address}:{self.network_location.port}')
        consumer.request({
            'command': fsgui.spikegadgets.action.generate_statescript(
                function_num=config['functNum'],
                pre_delay=config['preDelay'],
                n_pulses=config['nPulses'],
                n_trains=config['nOutputTrains'],
                train_interval=config['trainInterval'],
                sequence_period=config['sequencePeriod'],
                primary_stim_pin=config['primaryBit'],
                pulse_length=config['pulseLength']
            ),
        })

        return fsgui.spikegadgets.action.build_shortcut_command(
            sub_addresses=address_map,
            filter_tree=config['filter_id'],
            network_location=self.network_location,
            lockout_time=config['lockout_time'],
            on_funct_num=config['functNum'],
            off_funct_num=config['functNum'] + 1,
        )
