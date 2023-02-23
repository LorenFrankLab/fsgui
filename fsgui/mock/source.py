import multiprocessing as mp
import fsgui.process
import fsgui.network
import fsgui.node
import random
import time
import json

class RandomGeneratorType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='MockRandomData',
            datatype='float',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'MockRandomData',
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
        if 'error' in config['nickname']:
            raise NotImplementedError('we need to implement this')
        return RandomGeneratorProcess()

class RandomGeneratorProcess:
    def __init__(self):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            import fsgui.network
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

        def workload(logging, messages, publisher, reporter, data):
            value = random.random()
            data['publisher'].send(f'{value}')
            time.sleep(0.01)

        def cleanup(data):
            pipe_send.close()

        self._enabled = False
        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()

        self.pub_address = pipe_recv.recv()

class BinGeneratorType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name='Bin generator type'
        super().__init__(
            type_id=type_id,
            node_class='source',
            name=name,
            datatype='bin_id',
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
        return BinGeneratorProcess()

class BinGeneratorProcess:
    def __init__(self):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

        def workload(logging, messages, publisher, reporter, data):
            value = random.choice(range(20))
            data['publisher'].send(f'{value}')
            time.sleep(0.01)

        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()

        self.pub_address = pipe_recv.recv()

class MockGamePositionType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='MockGamePosition',
            datatype='float',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Mock Game Position',
                'location': 'tcp://127.0.0.1:9990',
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
                'label': 'ZMQ Network Location',
                'name': 'location',
                'type': 'string',
                'default': config['location'],
                'tooltip': 'This is where the publisher server is.',
            },
 
        ]
    
    def build(self, config):
        return MockGamePositionProcess(config['location'])

class MockGamePositionProcess:
    def __init__(self, game_location):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            import fsgui.network
            data['game_receiver'] = fsgui.network.UnidirectionalChannelReceiver(game_location)
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

        def workload(logging, messages, publisher, reporter, data):
            value = data['game_receiver'].recv(timeout=500)
            if value is not None:
                value_splits = value.split(',')
                x = float(value_splits[0])
                y = float(value_splits[1])
                data['publisher'].send(f'[{x}, {y}]')

        def cleanup(data):
            receiver = data['game_receiver']
            del receiver

            publisher = data['publisher']
            del publisher

            pipe_send.close()

        self._enabled = False
        self._proc = fsgui.process.ProcessObject({'location': game_location }, setup, workload, cleanup)
        self._proc.start()
        self.pub_address = pipe_recv.recv()
    
class LFPPlaybackType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='MockFileLFP',
            datatype='float',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Mock File LFP',
                'location': '',
                'hardware_sample_rate': 30000,
                'lfp_decimation': True,
                'lfp_decimation_factor': 20,
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
                'label': 'File path',
                'name': 'location',
                'type': 'string',
                'default': config['location'],
                'tooltip': 'This is the file to read from.',
            },
            {
                'label': 'Hardware sample rate (samples per second)',
                'name': 'hardware_sample_rate',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['hardware_sample_rate'],
                'tooltip': 'The rate at which the data were originally sampled.',
            },
            {
                'label': 'LFP decimation',
                'name': 'lfp_decimation',
                'type': 'boolean',
                'default': config['lfp_decimation'],
                'tooltip': 'Whether or not the LFP was subsampled.',
            },
            {
                'label': 'LFP decimation factor',
                'name': 'lfp_decimation_factor',
                'type': 'integer',
                'lower': 0,
                'upper': 100,
                'default': config['lfp_decimation_factor'],
                'tooltip': 'Factor by which lfp is decimated.',
            },
        ]
    
    def build(self, config):
        # account for decimation because the LFP is not reported by Trodes
        # at the same rate as the hardware

        if config['lfp_decimation']:
            sleep_time_s = 1.0 / config['hardware_sample_rate'] * config['lfp_decimation_factor']
        else:
            sleep_time_s = 1.0 / config['hardware_sample_rate']

        return LFPPlaybackProcess(config['location'], sleep_time_s)

class LFPPlaybackProcess:
    def __init__(self, filename, sleep_time_s):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

            with open(filename, 'r') as f:
                content = f.read()
            decoded = json.loads(content)
            data['lfps'] = decoded['datas']
            data['sample_index'] = 0

        def workload(logging, messages, publisher, reporter, data):
            loop_start_s = time.time()

            if not data['sample_index'] < len(data['lfps']):
                data['sample_index'] = 0

            sample = data['lfps'][data['sample_index']]
            data['sample_index'] += 1

            # this is the hard part
            data['publisher'].send(json.dumps(sample))

            surplus_s = sleep_time_s - (time.time() - loop_start_s)
            if surplus_s > 0:
                time.sleep(surplus_s)

        def cleanup(data):
            publisher = data['publisher']
            del publisher

            pipe_send.close()

        self._enabled = False
        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()
        self.pub_address = pipe_recv.recv()
