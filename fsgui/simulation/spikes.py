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
    
    def build(self, config, param_map):
        waveform_length = 40 # samples in a waveform
        n_tetrodes = 4 # number of waveforms

        n_simulated_neurons = 12

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

        def setup(connection, data):
            data['neurons'] = [
                np.array([random.randint(low, high) for ch in range(n_tetrodes)])
                for n in range(n_simulated_neurons)
            ]

            data['start_time'] = time.time()

        def workload(connection, publisher, reporter, data):
            neuron_id = random.randint(0, n_simulated_neurons-1)
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
                'spike': np.max(waveforms)
            })

            time.sleep(0.0006)
        
        return fsgui.process.build_process_object(setup, workload)
