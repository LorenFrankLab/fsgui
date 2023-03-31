import multiprocessing as mp
import fsgui.nparray
import fsgui.node
import json
import numpy as np
import time
import zmq
import functools
import itertools

class SpikeContentDecoder(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Spike content decoder',
            datatype='discrete_distribution',
        )

    def write_template(self, config = None):
        config = config if config is not None else {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'spikes_source': None,
            'covariate_source': None,
            'update_signal_source': None,
            'mark_ndims': 4,
            'bin_count': 1,
            'sigma': 1,
            'voltage_scaling_factor': 0.195,
            'minimum_spike_amplitude_filter': 100,
            'n_minimum_in_region': 10,
            'region_zscore': 1.96,
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
                'label': 'Spikes source (raw spikes)',
                'name': 'spikes_source',
                'type': 'node:spikes',
                'default': config['spikes_source'],
                'tooltip': 'This node provides raw spikes.',
            },
            {
                'label': 'Covariate source',
                'name': 'covariate_source',
                'type': 'node:bin_id',
                'default': config['covariate_source'],
                'tooltip': 'This node provides current value of the covariate to develop a prior.',
            },
            {
                'label': 'Update signal',
                'name': 'update_signal_source',
                'type': 'node:bool',
                'default': config['update_signal_source'],
                'tooltip': 'This node provides a signal of whether or not to update the model.',
            },
            {
                'label': 'Mark dimensions',
                'name': 'mark_ndims',
                'type': 'integer',
                'lower': 1,
                'upper': 256,
                'default': config['mark_ndims'],
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
            {
                'label': 'Sigma',
                'name': 'sigma',
                'type': 'double',
                'lower': 0,
                'upper': 10000,
                'default': config['sigma'],
                'tooltip': 'Sigma controls the width of the kernel; a larger sigma is a wider kernel',
                'live_editable': True,
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
            {
                'label': 'Spike Filter: minimum spike amplitude',
                'name': 'minimum_spike_amplitude_filter',
                'type': 'double',
                'lower': 0,
                'upper': 10000,
                'decimals': 2,
                'default': config['minimum_spike_amplitude_filter'],
                'live_editable': True,
            },
            {
                'label': 'Spike Filter: minimum spikes in a region',
                'name': 'n_minimum_in_region',
                'type': 'integer',
                'lower': 0,
                'upper': 10000,
                'default': config['n_minimum_in_region'],
                'live_editable': True,
            },
            {
                'label': 'Spike Filter: region z-score',
                'name': 'region_zscore',
                'type': 'double',
                'lower': 0,
                'upper': 10000,
                'decimals': 2,
                'default': config['region_zscore'],
                'live_editable': True,
            },
        ]
    
    def build(self, config, addr_map):
        config['waveform_length'] = 40

        spikes_address=addr_map[config['spikes_source']]
        covariate_address=addr_map[config['covariate_source']]
        update_address=addr_map[config['update_signal_source']]

        def setup(reporter, data):
            data['spikes_sub'] = fsgui.network.UnidirectionalChannelReceiver(spikes_address)
            data['covariate_sub'] = fsgui.network.UnidirectionalChannelReceiver(covariate_address)
            data['update_sub'] = fsgui.network.UnidirectionalChannelReceiver(update_address)

            # use polling to receive from multiple pubs without blocking in sequence
            data['poller'] = zmq.Poller()
            data['poller'].register(data['spikes_sub'].sock)
            data['poller'].register(data['covariate_sub'].sock)
            data['poller'].register(data['update_sub'].sock)

            # data['mark_calculator'] = MarkCalculator()
            data['mark_calculator'] = MarkCalculatorNative(config['mark_ndims'], config['waveform_length'])
            data['mark_encoder'] = MarkSpaceEncoderSynchronous(
                bin_count=config['bin_count'],
                mark_ndims=config['mark_ndims'],
                kernel_sigma=config['sigma'],
                n_minimum_in_region=config['n_minimum_in_region'],
                region_zscore=config['region_zscore']
            )

            data['update_model_bool'] = False
            data['current_covariate_value'] = None

            # timing code
            data['timestats'] = {
                't': {},
                'stats': {},
                'track': [1,2,3,4,5],
            }
            for i in data['timestats']['track']:
                data['timestats']['stats'][i] = []


            data['iteration'] = 0

        def workload(connection, publisher, reporter, data):
            t = data['timestats']['t']
            stats = data['timestats']['stats']
            track = data['timestats']['track']

            t[0] = time.time()

            results = dict(data['poller'].poll(timeout=500))

            t[1] = time.time()

            # update signals from the GUI
            if connection.pipe_poll(timeout = 0):
                msg_tag, msg_data = connection.pipe_recv()
                if msg_tag == 'update':
                    msg_varname, msg_value = msg_data
                    # update mark encoder variables
                    if msg_varname in ['sigma', 'n_minimum_in_region', 'region_zscore']:
                        config[msg_varname] = msg_value

                        data['mark_encoder'].update_config(
                            kernel_sigma=config['sigma'],
                            n_minimum_in_region=config['n_minimum_in_region'],
                            region_zscore=config['region_zscore']
                        )

            t[2] = time.time()

            # update sub
            if data['update_sub'].sock in results:
                item = data['update_sub'].recv()
                data['update_model_bool'] = item

            t[3] = time.time()
 
            # update covariate
            if data['covariate_sub'].sock in results:
                item = data['covariate_sub'].recv()
                data['current_covariate_value'] = item

            t[4] = time.time()

            if data['spikes_sub'].sock in results:
              
                spikes_data = data['spikes_sub'].recv()

                tetrode_id = spikes_data['nTrodeId']
                bin_id = data['current_covariate_value']

                mark = data['mark_calculator'].compute_mark(spikes_data['samples'])


                query_histogram = data['mark_encoder'].query_mark(tetrode_id, mark)


                if data['update_model_bool']:
                    data['mark_encoder'].add_mark(tetrode_id, mark, data['current_covariate_value'])

            t[5] = time.time()

            # deposit data into a thing
            # time bin buffer
            for i in track:
                stats[i].append(t[i] - t[i-1])



            data['iteration'] += 1
            if data['iteration'] % 100 == 0:
                for i in track:
                    print(f'time {i}: {np.mean(stats[i])*6:.6f}us (sum {np.sum(stats[i])*6:.6f}us)')

                for i in data['mark_calculator'].track:
                    stats = data['mark_calculator'].stats
                    print(f'marktime {i}: {np.mean(stats[i])*6:.6f}us (sum {np.sum(stats[i])*6:.6f}us)')



        return fsgui.process.build_process_object(setup, workload)
    
class EncodedSpikeBuffer:
    def __init__(self):
        pass

    def add_spike(self, timestamp, tetrode_id, bin_id, query_histogram):
        pass

    def get_buffer(self, timestamp):
        pass

class MarkCalculator:
    def __init__(self):
        self.t = {}
        self.stats = {}
        self.track = [1,2,3,4,5,6]
        for i in self.track:
            self.stats[i] = []
    
    def compute_mark(self, samples):
        self.t[0] = time.time()
        datapoint = np.array(samples)
        self.t[1] = time.time()
        spike_data = np.atleast_2d(datapoint.data)
        self.t[2] = time.time()
        channel_peaks = np.max(spike_data, axis=1)
        self.t[3] = time.time()
        peak_channel_ind = np.argmax(channel_peaks)
        self.t[4] = time.time()
        t_ind = np.argmax(spike_data[peak_channel_ind])
        self.t[5] = time.time()
        amp_mark = spike_data[:, t_ind]
        self.t[6] = time.time()

        for i in self.track:
            self.stats[i].append(self.t[i] - self.t[i-1])


        return amp_mark

class MarkCalculatorNative:
    def __init__(self, mark_ndims, waveform_length):
        self.mark_ndims = mark_ndims
        self.waveform_length = waveform_length

        self.t = {}
        self.stats = {}
        self.track = [1,2,3,4]
        for i in self.track:
            self.stats[i] = []
    
    
    def compute_mark(self, samples):
        self.t[0] = time.time()
        highest_index = 0
        highest_value = -1

        self.t[1] = time.time()
        for channel in range(self.mark_ndims):
            value = max(samples[channel])
            if value > highest_value:
                highest_index = samples[channel].index(value)
                highest_value = value
        self.t[2] = time.time()
        mark = [samples[ch][highest_index] for ch in range(self.mark_ndims)]
        self.t[3] = time.time()
        mark = np.array(mark)
        self.t[4] = time.time()

        for i in self.track:
            self.stats[i].append(self.t[i] - self.t[i-1])

        return mark

class MarkSpaceEncoderSynchronous:
    def __init__(self, bin_count, mark_ndims, kernel_sigma, n_minimum_in_region, region_zscore):
        self.bin_count = bin_count
        self.mark_ndims = mark_ndims

        self.update_config(
            kernel_sigma=kernel_sigma,
            n_minimum_in_region=n_minimum_in_region,
            region_zscore=region_zscore
        )

        self.kernel_sigma = kernel_sigma
        self.n_minimum_in_region = n_minimum_in_region
        self.region_zscore = region_zscore

        self.observations_per_tetrode = {}

    def add_mark(self, tetrode_id, mark, covariate):
        if tetrode_id not in self.observations_per_tetrode:
            self.observations_per_tetrode[tetrode_id] = (
                fsgui.nparray.ArrayList(width=self.mark_ndims, dtype='float'),
                fsgui.nparray.ArrayListSingleWidth(dtype='int16'),
            )

        mark_history, covariate_history = self.observations_per_tetrode[tetrode_id]
        mark_history.place(mark)
        covariate_history.place(covariate)
    
    def query_mark(self, tetrode_id, mark):
        # make sure to pass in marks that are:
        # 1. already scaled
        # 2. have their dead channels zeroed out
        # 3. are only from tetrodes we care about
        if tetrode_id not in self.observations_per_tetrode:
            return None

        if self.__calculate_filter(tetrode_id, mark):
            return self.__calculate_histogram(tetrode_id, mark)
        else:
            return None
        
    def __calculate_normalized_occupancy(self, tetrode_id):
        _, covariate_history = self.observations_per_tetrode[tetrode_id]
        covariate_history = covariate_history.get_slice()

        occupancy_histogram = np.bincount(
            covariate_history,
            minlength=self.bin_count)
        occupancy_histogram[occupancy_histogram == 0] = np.mean(occupancy_histogram)
        return occupancy_histogram / np.sum(occupancy_histogram)

    def __calculate_histogram(self, tetrode_id, mark):
        mark_history, covariate_history = self.observations_per_tetrode[tetrode_id]
        mark_history = mark_history.get_slice()
        covariate_history = covariate_history.get_slice()

        history_squared_distances = np.sum(
            np.square(mark_history - mark),
            axis=1
        )

        # larger k2 is narrower kernel, smaller k2 is wider kernel
        history_weights = self._k1 * np.exp(self._k2 * history_squared_distances)
        # necessary to remove super tiny weights because bug in numpy histograms
        history_weights[history_weights < 1e-20] = 0

        query_histogram = np.bincount(
            covariate_history,
            weights=history_weights,
            minlength=self.bin_count)

        return query_histogram / self.__calculate_normalized_occupancy(tetrode_id)

    def __calculate_filter(self, tetrode_id, mark):
        mark_history, _ = self.observations_per_tetrode[tetrode_id]
        mark_history = mark_history.get_slice()

        # this is counting spikes within a hypercube around the mark
        return np.sum(
            functools.reduce(
                np.logical_and,
                itertools.chain.from_iterable([
                    [
                        mark_history[:,dim] > mark[dim] - self._region_half_box_width,
                        mark_history[:,dim] < mark[dim] + self._region_half_box_width,
                    ]
                    for dim in range(self.mark_ndims)
                ]
        ))) >= self.n_minimum_in_region

    def update_config(self, *, kernel_sigma, n_minimum_in_region, region_zscore):
        self.kernel_sigma = kernel_sigma
        self.n_minimum_in_region = n_minimum_in_region
        self.region_zscore = region_zscore

        self._k1 = 1 / (np.sqrt(2*np.pi) * self.kernel_sigma)
        self._k2 = -0.5 / (self.kernel_sigma**2)

        self._region_half_box_width = self.region_zscore * self.kernel_sigma

class OccupancyHistory:
    def __init__(self, bin_count):
        self.bin_count = bin_count

        self.observations = 0
        self.covariate_occupancy = np.zeros(shape=(self.bin_count,))

    def add_covariate_observation(self, covariate):
        self.covariate_occupancy[covariate] += 1
        self.observations += 1

    def calculate_normalized_occupancy(self):
        if self.observations == 0:
            return np.ones(shape=(self.bin_count, )) / self.bin_count

        return self.covariate_occupancy / self.observations

class FiringHistory:
    def __init__(self, bin_count):
        self.firing_per_tetrode = {}
    
    def add_spike_observation(self, tetrode_id, covariate):
        if tetrode_id not in self.firing_per_tetrode:
            self.firing_per_tetrode[tetrode_id] = np.zeros(shape=(self.bin_count,))
        self.firing_per_tetrode[tetrode_id][covariate] += 1
    
    def calculate_firing_rates(self, tetrode_id):
        # double check
        return self.firing_per_tetrode[tetrode_id] / np.sum(self.firing_per_tetrode[tetrode_id])
    
    def get_tetrodes_in_history(self):
        return set(self.firing_per_tetrode.keys())

class LikelihoodCalculator:
    # likelihood of observing this spike sequence
    def __init__(self, bin_count, firing_history, epsilon=1e-7):
        self.bin_count = bin_count
        self.firing_history = firing_history
        self.epsilon = epsilon

    def calculate_likelihood_timebin_independent_spikes_poisson(self, spikes, dt):
        likelihood_contributions = []

        # find out which tetrodes didn't have any firing on them.
        tetrodes_no_spikes = self.firing_history.get_tetrodes_in_history() - set([spike['tetrode_id'] for spike in spikes])
        for tetrode_id in tetrodes_no_spikes:
            normalized_firing_rates = self.firing_history.calculate_firing_rates(tetrode_id)
            # calculate likelihood that these tetrodes would have no spikes
            likelihood_contribution = np.exp(-dt * normalized_firing_rates)
            likelihood_contributions.append(likelihood_contribution)

        for spike in spikes:
            likelihood_contribution = spike['histogram']
            if likelihood_contribution is not None:
                likelihood_contributions.append(likelihood_contribution)

        # multiply each likelihood of each event
        # assuming everything is independent
        likelihood = np.ones(shape=(self.bin_count,)) / self.bin_count
        for likelihood_contribution in likelihood_contributions:
            likelihood_contribution[likelihood_contribution < self.epsilon] = self.epsilon
            # check for numerical stability, can use log-likelihood method if this doesn't work
            likelihood *= likelihood_contribution
        
        return likelihood / np.sum(likelihood)
        
class BayesianPosteriorEstimator:
    # uses the prior
    def __init__(self, bin_count, transition_matrix):
        self.bin_count = bin_count
        self.transition_matrix = transition_matrix

        # just assume the last estimate was uninformative
        self.last_posterior = np.ones((self.bin_count,)) / self.bin_count
    
    def __compute_prior(self):
        return self.last_posterior @ self.transition_matrix
    
    def compute_posterior(self, likelihood):
        self.last_posterior = likelihood * self.__compute_prior()
        return self.last_posterior
