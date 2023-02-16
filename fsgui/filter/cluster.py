import multiprocessing as mp
import fsgui.node
import zmq

class DecoderType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name='Point process decoder'
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name=name,
            datatype='discrete_distribution',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'histogram_source': None,
                'timekeeper_source': None,
                'covariate_source': None,
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
        ]
    def build(self, config, addr_map):

        decoder = Decoder(
            transition_matrix=None,
            )

        return DecoderProcess(
            histogram_address=addr_map[config['histogram_source']],
            timekeeper_address=addr_map[config['timekeeper_source']],
            covariate_address=addr_map[config['covariate_source']],
            decoder=decoder)

class DecoderProcess:
    def __init__(self, histogram_address, timekeeper_address, covariate_address, decoder):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            data['histogram_sub'] = fsgui.network.UnidirectionalChannelReceiver(histogram_address)
            data['timekeeper_sub'] = fsgui.network.UnidirectionalChannelReceiver(timekeeper_address)
            data['covariate_sub'] = fsgui.network.UnidirectionalChannelReceiver(covariate_address)

            # use polling to receive from multiple pubs without blocking in sequence
            data['poller'] = zmq.Poller()
            for sub_var_name in ['histogram_sub', 'timekeeper_sub', 'covariate_sub']:
                data['poller'].register(data[sub_var_name].sock)

            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

            data['filter_model'] = decoder

        def workload(data):
            results = dict(data['poller'].poll(timeout=500))

            if data['histogram_sub'].sock in results:
                print('have a spike')
                item = data['histogram_sub'].recv(timeout=500)

                # add things to the buffer

            if data['timekeeper_sub'].sock in results:
                item = data['timekeeper_sub'].recv(timeout=500)

                # run a decode on the spikes in buffer
                # result = data['filter_model'].query(buffer_spikes)
                # data['publisher'].send(f'{result}')

            if data['covariate_sub'].sock in results:
                item = data['covariate_sub'].recv(timeout=500)
                data['filter_model'].update_covariate(int(item))
 
        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()
        self.pub_address = pipe_recv.recv()




class RealtimeSpikeBuffer:
    def __init__(self, time_bin_width, time_bin_delay, size=1000):
        self.time_bin_width
        self.time_bin_delay
        self.size = size

        self.buffer = np.zeros(size)

    def enqueue_spike(self, group, pos, timestamp):
        self.buffer
        pass

    def dequeue_spikes_bin(self, timestamp):
        pass        

        spikes_in_bin_mask = np.logical_and(
            self.decoded_spike_array[:, 0] >= self.decoder_timestamp - self.decoder_bin_delay*self.time_bin_size,
            self.decoded_spike_array[:, 0] < self.decoder_timestamp - self.decoder_bin_delay*self.time_bin_size + self.time_bin_size)
        
        # remove duplicates based on timestamp

class Decoder:
    def __init__(self, transition_matrix):
        self.transition_matrix = transition_matrix

    def add_observation(self, group, covariate_histogram):
        self.firing_rate[group][self.current_covariate_bin] += 1
        pass

    def update_covariate(self, covariate_value):
        self.current_covariate_value = covariate_value
        
    def __increment_bin(self):
        pass

    def __increment_no_bin(self):
        pass

    def process_observations(self, observations):
        for group, covariate_histogram in observations:
            self.add_observation(group, covariate_histogram)

        if len(observations) == 0:
            posterior, likelihood = self.__increment_no_bin()
        else:
            posterior, likelihood = self.__increment_bin()

        return posterior
        
class ArmPosterior:
    def __update_posterior_stats(self):
        pass
