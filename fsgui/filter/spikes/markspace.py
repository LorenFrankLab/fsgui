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
        name='Mark space kernel encoder'
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name=name,
            datatype='discrete_distribution',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'spikes_source': None,
                'covariate_source': None,
                'update_signal_source': None,
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
        ]
    
    def build(self, config, addr_map):

        spikes_address=addr_map[config['spikes_source']]
        covariate_address=addr_map[config['covariate_source']]
        update_address=addr_map[config['update_signal_source']]

        encoder = MarkSpaceEncoder(
            mark_ndims=1,
            covariate_histogram_bins=40,
            weighting_algorithm=None,
            k1=5,
            k2=2,
            )

        def setup(reporter, data):
            data['spikes_sub'] = fsgui.network.UnidirectionalChannelReceiver(spikes_address)
            data['covariate_sub'] = fsgui.network.UnidirectionalChannelReceiver(covariate_address)
            data['update_sub'] = fsgui.network.UnidirectionalChannelReceiver(update_address)

            # use polling to receive from multiple pubs without blocking in sequence
            data['poller'] = zmq.Poller()
            data['poller'].register(data['spikes_sub'].sock)
            data['poller'].register(data['covariate_sub'].sock)
            data['poller'].register(data['update_sub'].sock)

            data['filter_model'] = encoder
            data['update_model_bool'] = False

        def workload(connection, publisher, reporter, data):
            start_time = time.time()
            results = dict(data['poller'].poll(timeout=500))

            if data['spikes_sub'].sock in results:
                print('have a spike')
                item = data['spikes_sub'].recv(timeout=500)
                print(f'time: {(time.time() - start_time) * 1000.0}ms')

                # we have a spike
                spikes_data = json.loads(item)
                samples = np.array(spikes_data['samples'])
                # print(f'spikes: {samples.shape}')
                # print(f'samples: {samples}')
                # print(f't2me: {(time.time() - start_time) * 1000.0}ms')

                mark = samples[:,5]

                result = data['filter_model'].query(mark)
                print(result)
                publisher.send(f'{result}')

                if data['update_model_bool']:
                    data['filter_model'].add_mark(mark)

            if data['update_sub'].sock in results:
                item = data['update_sub'].recv(timeout=500)
                data['update_model_bool'] = bool(item)

            if data['covariate_sub'].sock in results:
                item = data['covariate_sub'].recv(timeout=500)
                data['filter_model'].update_covariate(int(item))

        return fsgui.process.build_process_object(setup, workload)

class MarkSpaceDistance:
    pass

class MarkSpaceFilter:
    pass

class MarkSpaceEncoder:
    def __init__(self, mark_ndims, covariate_histogram_bins, weighting_algorithm, k1, k2, marks_filter=None):
        self.k1 = k1
        self.k2 = k2

        self.observations_mark = fsgui.nparray.ArrayList(width=mark_ndims, dtype='float')
        self.observations_covariate = fsgui.nparray.ArrayList(width=mark_ndims, dtype='float')

        self.histogram_bins = covariate_histogram_bins
        self.weighting = weighting_algorithm
        self.filter = marks_filter

        self.current_covariate_value = None

    def update_covariate(self, covariate_value):
        self.current_covariate_value = covariate_value

    def add_mark(self, mark_value):
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

        query_weights = self.k1 * np.exp(squared_distance * self.k2)
        query_covariates = self.observations_covariate.get_slice()

        query_histogram, query_histogram_edges = np.histogram(
            a=query_covariates, bins=self.histogram_bins,
            weights=query_weights, normed=False
        )

    def __normalize_histogram(self, histogram):
        histogram += 1e-7
        # histogram /= self

        # normalize by normalized occupancy
        # set nan to zero
        # normalized by self histogram times bin width to become a pdf

    def query(self, m):
        if self.__calculate_filter(m):
            return self.__calculate_histogram(m)
        else:
            return None