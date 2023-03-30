import multiprocessing as mp
import fsgui.nparray
import fsgui.node
import json
import numpy as np
import time
import zmq
import functools
import itertools

class MarkSpaceEncoderType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Mark space kernel encoder',
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
        ]
    
    def build(self, config, addr_map):
        spikes_address=addr_map[config['spikes_source']]
        covariate_address=addr_map[config['covariate_source']]
        update_address=addr_map[config['update_signal_source']]

        encoder = MarkSpaceEncoder(
            mark_ndims=config['mark_ndims'],
            bin_count=config['bin_count'],
            sigma=config['sigma'],
        )


        def compute_mark(datapoint):
            spike_data = np.atleast_2d(datapoint.data)
            channel_peaks = np.max(spike_data, axis=1)
            peak_channel_ind = np.argmax(channel_peaks)
            t_ind = np.argmax(spike_data[peak_channel_ind])
            amp_mark = spike_data[:, t_ind]

            return amp_mark

        def setup(reporter, data):
            data['spikes_sub'] = fsgui.network.UnidirectionalChannelReceiver(spikes_address)
            data['covariate_sub'] = fsgui.network.UnidirectionalChannelReceiver(covariate_address)
            data['update_sub'] = fsgui.network.UnidirectionalChannelReceiver(update_address)

            # use polling to receive from multiple pubs without blocking in sequence
            data['poller'] = zmq.Poller()
            data['poller'].register(data['spikes_sub'].sock)
            data['poller'].register(data['covariate_sub'].sock)
            data['poller'].register(data['update_sub'].sock)

            data['filter_model'] = {}
            data['update_model_bool'] = False
            data['current_covariate_value'] = None

        def workload(connection, publisher, reporter, data):
            start_time = time.time()
            results = dict(data['poller'].poll(timeout=500))

            if connection.pipe_poll(timeout = 0):
                msg_tag, msg_data = connection.pipe_recv()
                if msg_tag == 'update':
                    msg_varname, msg_value = msg_data
                    if msg_varname == 'sigma':
                        for model in data['filter_model'].values():
                            model.update_sigma(msg_value)

            if data['spikes_sub'].sock in results:
                spikes_data = data['spikes_sub'].recv()
                # we have a spike
                samples = np.array(spikes_data['samples'])
                received_time = time.time()

                mark = compute_mark(samples)

                query_result = data['filter_model'].setdefault(spikes_data['nTrodeId'], MarkSpaceEncoder(mark_ndims=config['mark_ndims'], bin_count=config['bin_count'], sigma=config['sigma'])).query(mark)
                if query_result is not None:
                    query_histogram_normalized = query_result[0].tolist()
                    query_histogram = query_result[1].tolist()
                    occupancy_histogram = query_result[2].tolist()
                    occupancy_histogram_normalized = query_result[3].tolist()
                    distance_dist = query_result[4].tolist()
                    weights_dist = query_result[5].tolist()
                else:
                    query_histogram_normalized = None
                    query_histogram = None
                    occupancy_histogram = None
                    occupancy_histogram_normalized = None
                    distance_dist = None
                    weights_dist = None

                time_query = time.time()

                publisher.send({
                    'timestamp': spikes_data['localTimestamp'],
                    'electrode_group_id': spikes_data['nTrodeId'],
                    'histogram': query_histogram_normalized,
                    'bin_id': data['current_covariate_value'],
                })

                reporter.send({
                    # 'spike_received_time': received_time - start_time,
                    # 'query_time': time_query - start_time,
                    'me_mark': mark.tolist(),
                    'me_query_histogram': query_histogram,
                    'me_occupancy_histogram': occupancy_histogram,
                    'me_distance_dist': distance_dist,
                    'me_weights_dist': weights_dist,
                    'me_covariate': np.bincount([data['current_covariate_value']], minlength=config['bin_count']).tolist() if data['current_covariate_value'] is not None else None,
                })

                if data['update_model_bool']:
                    data['filter_model'].get(spikes_data['nTrodeId']).add_mark(mark)

            if data['update_sub'].sock in results:
                item = data['update_sub'].recv(timeout=500)
                data['update_model_bool'] = bool(item)

            if data['covariate_sub'].sock in results:
                item = data['covariate_sub'].recv(timeout=500)
                for model in data['filter_model'].values():
                    model.update_covariate(int(item))
                data['current_covariate_value'] = int(item)

        return fsgui.process.build_process_object(setup, workload)

class MarkSpaceEncoder:
    def __init__(self, mark_ndims, bin_count=20, sigma=1):
        self.bin_count = bin_count

        # Gaussian kernel parameters
        self.update_sigma(sigma)

        self.current_covariate_value = None
        self.observations_mark = fsgui.nparray.ArrayList(width=mark_ndims, dtype='float')
        self.observations_covariate = fsgui.nparray.ArrayList(width=1, dtype='float')
    
    def update_sigma(self, sigma):
        self._k1 = 1 / (np.sqrt(2*np.pi) * sigma)
        self._k2 = -0.5 / (sigma**2)

    def update_covariate(self, covariate_value):
        self.current_covariate_value = covariate_value

    def add_mark(self, mark_value):
        if self.current_covariate_value is not None:
            self.observations_mark.place(mark_value)
            self.observations_covariate.place(self.current_covariate_value)

    def __calculate_filter(self, mark_value):
        # these are configurations
        n_std, std = (5, 20)
        n_marks_min = 10

        half_box_width = n_std * std

        return np.sum(
            functools.reduce(
                np.logical_and,
                itertools.chain.from_iterable([
                    [
                        self.observations_mark.get_slice()[:,dim] > mark_value[dim] - half_box_width,
                        self.observations_mark.get_slice()[:,dim] < mark_value[dim] + half_box_width,
                    ]
                    for dim in range(self.observations_mark.get_slice().shape[1])
                ]
        ))) >= n_marks_min

    def __calculate_histogram(self, mark_value):

        squared_distance = np.sum(
            np.square(self.observations_mark.get_slice() - mark_value),
            axis=1
        )

        # larger k2 is narrower kernel, smaller k2 is wider kernel
        observation_weights = self._k1 * np.exp(self._k2 * squared_distance)
        # necessary to remove super tiny weights because bug in numpy histograms
        observation_weights[observation_weights < 1e-20] = 0
        observation_covariates = self.observations_covariate.get_slice().flatten().astype(np.int32)

        query_histogram = np.bincount(
            observation_covariates,
            weights=observation_weights,
            minlength=self.bin_count)

        occupancy_histogram = np.bincount(
            observation_covariates,
            minlength=self.bin_count)
        occupancy_histogram_normalized = occupancy_histogram / np.sum(occupancy_histogram)
        occupancy_histogram_normalized[occupancy_histogram_normalized == 0] = 0.0001

        query_histogram_normalized = query_histogram / occupancy_histogram_normalized

        # for debugging
        distance_dist, _ = np.histogram(squared_distance, bins = 30)
        weights_dist, _ = np.histogram(observation_weights, bins = 30)

        return (
            # this is the main value we need
            query_histogram_normalized,
            query_histogram,
            occupancy_histogram,
            occupancy_histogram_normalized,
            distance_dist,
            weights_dist,
            )

    def query(self, m):
        if self.__calculate_filter(m):
            return self.__calculate_histogram(m)
        else:
            return None