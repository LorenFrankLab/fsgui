import multiprocessing as mp
import fsgui.node
import zmq
import time
import numpy as np

class DecoderType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name='Point process decoder'
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name=name,
            datatype='discrete_distribution',
            default=None,
        )

    def write_template(self, config = None):
        config = config if config is not None else {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'histogram_source': None,
            'timekeeper_source': None,
            'covariate_source': None,
            'bin_count': 1,
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
                'label': 'Histogram source (encoded spikes)',
                'name': 'histogram_source',
                'type': 'node:discrete_distribution',
                'default': config['histogram_source'],
                'tooltip': 'This node provides a histogram distribution of the covariate.',
            },
            {
                'label': 'Timekeeper source',
                'name': 'timekeeper_source',
                'type': 'node:timestamp',
                'default': config['timekeeper_source'],
                'tooltip': 'This node provides regular time signal (decimated by factor of 20).',
            },
           {
                'label': 'Covariate source',
                'name': 'covariate_source',
                'type': 'node:bin_id',
                'default': config['covariate_source'],
                'tooltip': 'This node provides current value of the covariate to develop a prior.',
            },
            {
                'label': 'Bin count',
                'name': 'bin_count',
                'type': 'integer',
                'lower': 1,
                'upper': 256,
                'default': config['bin_count'],
                'tooltip': 'The number of bins the covariate has. This should be the maximum bin_id + 1.'
            },
        ]
    def build(self, config, addr_map):
        histogram_address=addr_map[config['histogram_source']]
        timekeeper_address=addr_map[config['timekeeper_source']]
        covariate_address=addr_map[config['covariate_source']]

        def create_uniform_transition(n):
            return np.ones((n, n)) / n
        
        def create_local_transition(n):
            P = np.zeros((n, n))  # transition matrix
            for i in range(n):
                P[i, (i-1)%n] = 0.15  # probability of transitioning to i-1
                P[i, i] = 0.7  # probability of staying at i
                P[i, (i+1)%n] = 0.15  # probability of transitioning to i+1
            return np.linalg.matrix_power(P, 5) + create_uniform_transition(n) * 0.01

        decoder = Decoder(
            bin_count=config['bin_count'],
            transition_matrix = create_uniform_transition(config['bin_count'])
        )

        def setup(reporter, data):
            data['histogram_sub'] = fsgui.network.UnidirectionalChannelReceiver(histogram_address)
            data['timekeeper_sub'] = fsgui.network.UnidirectionalChannelReceiver(timekeeper_address)
            data['covariate_sub'] = fsgui.network.UnidirectionalChannelReceiver(covariate_address)

            # use polling to receive from multiple pubs without blocking in sequence
            data['poller'] = zmq.Poller()
            for sub_var_name in ['histogram_sub', 'timekeeper_sub', 'covariate_sub']:
                data['poller'].register(data[sub_var_name].sock)

            data['filter_model'] = decoder

            data['spike_buffer'] = []

        def workload(connection, publisher, reporter, data):
            results = dict(data['poller'].poll(timeout=500))

            if data['histogram_sub'].sock in results:
                item = data['histogram_sub'].recv(timeout=0)

                # add things to the buffer
                data['spike_buffer'].append(item)

            if data['timekeeper_sub'].sock in results:
                data['timekeeper_sub'].recv(timeout=0)

                t0 = time.time()
                
                spikes_processed = len(data['spike_buffer'])

                # run a decode on the spikes in buffer
                result = data['filter_model'].compute_posterior(data['spike_buffer'])

                posterior = result[0].tolist()
                likelihood = result[1].tolist()
                prior = result[2].tolist()
                transitioned_prior = result[3].tolist()

                data['spike_buffer'] = []

                t1 = time.time()

                publisher.send(posterior)

                reporter.send({
                    'spikes_processed': spikes_processed,
                    'processing_time': (t1-t0) * 1000,
                    'dec_posterior': posterior,
                    'dec_likelihood': likelihood,
                    'dec_prior': prior,
                    'dec_transitioned_prior': transitioned_prior,
                    'dec_covariate': np.bincount([data['filter_model'].current_covariate_value], minlength=config['bin_count']).tolist() if data['filter_model'].current_covariate_value is not None else None,
                })

            if data['covariate_sub'].sock in results:
                item = data['covariate_sub'].recv(timeout=0)
                data['filter_model'].update_covariate(int(item))
 
        return fsgui.process.build_process_object(setup, workload)

class Decoder:
    def __init__(self, bin_count, transition_matrix):
        self.bin_count = bin_count

        assert transition_matrix.shape == (self.bin_count, self.bin_count)
        self.transmat = transition_matrix

        self._occupancy_array = fsgui.nparray.ArrayList(width=1)
        self.current_covariate_value = None

        # start with an uninformative prior
        self._prior = self.__normalize(np.ones((self.bin_count,)))

        # maps electrode groups to histograms of where they fired
        self._firing_rate = {}

    @property
    def occupancy(self):
        if self._occupancy_array.get_slice().shape[0] > 0:
            return np.bincount(
                self._occupancy_array.get_slice().flatten().astype(np.int32),
                minlength=self.bin_count)
        else:
            return np.zeros((self.bin_count,))

    def update_covariate(self, covariate_value, update_covariate=True):
        if update_covariate:
            self._occupancy_array.place(covariate_value)
            self.current_covariate_value = covariate_value
        
    def __normalize(self, array):
        if np.sum(array) != 0:
            return array / np.sum(array)
        else:
            return array

    def compute_posterior(self, observations):
        # update firing rates
        for obs in observations:
            group = obs['electrode_group_id']
            bin_id = obs['bin_id']
            self._firing_rate.setdefault(group, np.ones(self.bin_count,))[bin_id] += 1

        # start with basic likelihood
        likelihood = self.__normalize(np.ones((self.bin_count,)))
        occupancy_normalized = self.__normalize(self.occupancy)
        occupancy_normalized[occupancy_normalized == 0] = 1e-7

        dt = 180 / 30000.0

        # no spike contribution
        for elec_grp_id, firing_rates in self._firing_rate.items():
            normed_firing_rates = self.__normalize(firing_rates)
            likelihood_no_spike = np.exp(-dt * normed_firing_rates / occupancy_normalized)
            likelihood_no_spike[likelihood_no_spike == 0] = 1e-7
            likelihood *= likelihood_no_spike
            likelihood = self.__normalize(likelihood)
        
        # spike contribution
        for obs in observations:
            # at this point it would be good to replace zeros with small numbers
            histogram = obs['histogram']
            if histogram is not None:
                histogram[histogram == 0] = 1e-7
                likelihood = likelihood * histogram
                likelihood = self.__normalize(likelihood)

        transitioned_prior = (self._prior @ self.transmat)
        posterior = likelihood * transitioned_prior
        posterior = self.__normalize(posterior)

        # posterior becomes new prior for next round
        prior = self._prior
        self._prior = posterior
        return posterior, likelihood, prior, self.__normalize(transitioned_prior)