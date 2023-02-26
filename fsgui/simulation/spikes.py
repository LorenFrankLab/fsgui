import fsgui.node
import fsgui.process
import multiprocessing as mp
import random
import time
import numpy as np

class SpikesGeneratorType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name='Spikes generator'
        super().__init__(
            type_id=type_id,
            node_class='source',
            name=name,
            datatype='spikes',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'covariate_source': None,
                'n_simulated_neurons': 12,
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
                'label': 'Covariate source',
                'name': 'covariate_source',
                'type': 'node:bin_id',
                'default': config['covariate_source'],
                'tooltip': 'This node provides a position to affect firing.',
            },
            {
                'label': 'Number of simulated neurons',
                'name': 'n_simulated_neurons',
                'type': 'integer',
                'lower': 1,
                'upper': 64,
                'default': config['n_simulated_neurons'],
                'units': 'neurons',
                'tooltip': 'Number of neurons to simulate.'

            }
        ]
    
    def build(self, config, addr_map):
        covariate_address=addr_map[config['covariate_source']]

        waveform_length = 40 # samples in a waveform
        n_tetrodes = 4 # number of waveforms

        n_simulated_neurons = config['n_simulated_neurons']

        low = -5
        high = 5

        covariance_matrix = np.diag([0.5 for ch in range(n_tetrodes)])

        # create a characteristic waveform
        def action_potential(x):
            a = 0.5
            b = 1.5
            c = 2.0
            d = 3.0
            return a * np.exp(-(x-b)**2/(2*c**2)) - d * np.exp(-(x-b)**2/(2*(c/4)**2))

        # Generate 40 samples of the action potential waveform
        x = np.linspace(0, 5, 40)
        samples = -action_potential(x)
        waveform_schema = samples / np.max(samples)

        def transform_range(values, source_range, target_range):
            return np.interp(values, source_range, target_range)

        def setup(connection, data):
            data['covariate_sub'] = fsgui.network.UnidirectionalChannelReceiver(covariate_address)
            data['neurons'] = [
                np.array([random.randint(low, high) for ch in range(n_tetrodes)])
                for n in range(n_simulated_neurons)
            ]

            data['start_time'] = time.time()
            data['position'] = 0

            data['position_map'] = {}

        def workload(connection, publisher, reporter, data):
            covariate_value = data['covariate_sub'].recv(timeout=0)
            if covariate_value is not None:
                data['position'] = covariate_value

            # create a mapping so each position corresponds to firing one neuron
            neuron_id = data['position_map'].setdefault(data['position'], int(transform_range(data['position'], [0,20], [0, n_simulated_neurons])) % n_simulated_neurons)

            neuron = data['neurons'][neuron_id]
            mark = np.random.multivariate_normal(neuron, covariance_matrix)
            waveforms = [(waveform_schema * peak).tolist() for peak in mark]

            elapsed_time = time.time() - data['start_time']
            simulated_hardware_timestamp = int(elapsed_time * 30000)

            value = {
                'localTimestamp': simulated_hardware_timestamp,
                'nTrodeId': neuron_id,
                'samples': waveforms,
                'systemTimestamp': time.time_ns()
            }

            publisher.send(value)
            reporter.send({
                'spike': np.max(waveforms),
                'neuron_id': neuron_id,
            })

            time.sleep(0.01)
        
        return fsgui.process.build_process_object(setup, workload)
