import multiprocessing as mp
import numpy as np
import fsgui.network
import fsgui.process
import itertools
import logging

from PyQt6 import QtCore, QtWidgets

class MockFilterProvider:
    def get_nodes(self):
        return [
            MockFilter('mock-filter-type'),
            # PrinterFilterType('printer-filter-type'),
            # GraphingFilterType('graphing-filter-type'),
        ]

class MockFilter:
    def __init__(self, _type_id):
        self._type_id = _type_id
    def type_id(self):
        return self._type_id
    def node_class(self):
        return 'filter'
    def name(self):
        return 'Mock Filter'
    def datatype(self):
        return 'bool'
    def default(self):
        return {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'source_id': None,
        }

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
                'label': 'Source',
                'name': 'source_id',
                'type': 'node:float',
                'default': config['source_id'],
                'tooltip': 'Source to receive spatial data from',
            },
        ]
    def build(self, config, address_map):
        source_id = config['source_id']
        pub_address = address_map[source_id]
        return MockFilterProcess(pub_address)

class MockFilterProcess:
    def __init__(self, source_pub_address):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(source_pub_address)
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())
            data['filter_model'] = AverageFilterMath()

        def workload(data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                filtered = data['filter_model'].filter_speed(float(item))
                data['publisher'].send(f'{filtered}')

        def cleanup(data):
            pipe_send.close()

        self._enabled = False
        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._pub_address = pipe_recv.recv()

        self.enable()

    @property
    def pub_address(self):
        return self._pub_address

    @property
    def status(self):
        return 'enabled' if self._enabled else 'disabled'

    def enable(self):
        self._proc.start()
        self._enabled = True

    def disable(self):
        self._proc.pause()
        self._enabled = False

class AverageFilterMath:
    def __init__(self):
        self.history = []
    
    def filter_speed(self, x):
        self.history.append(x)
        if len(self.history) > 10:
            self.history = self.history[len(self.history)-10:]
        return np.mean(self.history) > 0.5

class MockFilterSimpleMathematical:
    def __init__(self):
        self.xpos = 0
        self.ypos = 0
        self.lastx = 0
        self.lasty = 0

    def reset_data(self):
        self.xpos = 0
        self.ypos = 0
        self.lastx = 0
        self.lasty = 0
   
    def filter_pos_speed(self, x, y):
        import math

        dx = x - self.lastx
        dy = y - self.lasty

        # not sure why they have 30
        speed = math.sqrt(dx * dx + dy * dy)

        lastx = x
        lasty = y

        return speed

class MockFilterMathematical:
    def __init__(self):
        self.nspeed_filt_points = 30
        self.speedFilterValues = [ 0.0393, 0.0392, 0.0391, 0.0389, 0.0387, 0.0385, 0.0382, 0.0379, 0.0375, 0.0371, 0.0367, 0.0362, 0.0357, 0.0352, 0.0347, 0.0341, 0.0334, 0.0328, 0.0321, 0.0315, 0.0307, 0.0300, 0.0293, 0.0285, 0.0278, 0.0270, 0.0262, 0.0254, 0.0246, 0.0238 ]
        self.stimOn = False
        self.stimChanged = False
        self.lastChange = 0
        self.xpos = 0
        self.ypos = 0
        self.inLockout = False

        self.cmPerPix = None

    def reset_data(self):
        self.speedFilt = [x for x in self.speedFilterValues]
        self.ind = self.nspeed_filt_points - 1
        self.lastx = 0
        self.lasty = 0
    
    def add_point(self, xposition, yposition, timestamp):
        currentStim = stimOn
        animalSpeed = filterPosSpeed(xpos, ypos)
        
        if (timestamp - lastChange) < self.lockoutTime:
            return stimOn

        if animalSpeed < self.minSpeed or animalSpeed > self.maxSpeed:
            stimOn = False
        else:
            pass
            # stimOn = (xpos >= self.lowerLeftX) and
            #             (xpos <= self.upperRightX) and
            #             (ypos >= self.lowerLeftY) and
            #             (ypos <= self.upperRightY)
        if stimOn != currentStim:
            stimChanged = True
            lastChange = timestamp
        return stimOn
    
    def filter_pos_speed(self, x, y):
        import math
        i = None
        tmpind = None
        # make sure can't crash
        smoothSpd = 0

        # Calculate instantaneous speed and adjust to cm/sec */

        dx = x * self.cmPerPix - self.lastx
        dy = y * self.cmPerPix - self.lasty

        # not sure why they have 30
        speed[self.ind] = math.sqrt(dx * dx + dy * dy) * 30.0

        lastx = x * self.cmPerPix
        lasty = y * self.cmPerPix


        # /* apply the filter to the speed points */
        for i in range(self.nspeed_filt_points):
            tmpind = (self.ind + i) % self.nspeed_filt_points;
            smoothSpd = smoothSpd + speed[tmpind] * self.speedFilt[i]
        self.ind -= 1
        if self.ind < 0:
            self.ind = self.nspeed_filt_points - 1

        return smoothSpd

class PrinterFilterType:
    def __init__(self, _type_id):
        self._type_id = _type_id
    def type_id(self):
        return self._type_id
    def name(self):
        return 'Printer Filter'
    
    def default(self):
        return {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'source_id': None,
        }

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
                'tooltip': 'This is the name the filter is displayed as in menus.',
            },
            {
                'label': 'Source',
                'name': 'source_id',
                'type': 'select',
                'options': list(itertools.chain(
                    [{'name': f'{source_id}', 'label': f'Source: {name}'} for name, source_id in info['sources']],
                    [{'name': f'{filter_id}', 'label': f'Filter: {name}'} for name, filter_id in info['filters']],
                )),
                'default': config['source_id'],
                'tooltip': 'Source from which to receive data and print.',
            },
        ]
    def build(self, source_object, config):
        source_process = source_object.built_object
        if source_process is None:
            raise ValueError("Source needs to be built")

        if source_process.pub_address is None:
            raise AssertionError

        return PrinterFilterProcess(source_process.pub_address)

class PrinterFilterProcess:
    def __init__(self, source_pub_address):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(source_pub_address)
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

        def workload(data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                data['publisher'].send(item)

                logging.info(f'Filter printing: {item}')

        def cleanup(data):
            pipe_send.close()

        self._enabled = False
        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._pub_address = pipe_recv.recv()

    @property
    def pub_address(self):
        return self._pub_address

    @property
    def status(self):
        return 'enabled' if self._enabled else 'disabled'

    def enable(self):
        self._proc.start()
        self._enabled = True

    def disable(self):
        self._proc.pause()
        self._enabled = False


class GraphingFilterType:
    def __init__(self, _type_id):
        self._type_id = _type_id
    def type_id(self):
        return self._type_id
    def name(self):
        return 'Graphing Filter'
    
    def default(self):
        return {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'source_id': None,
        }

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
                'tooltip': 'This is the name the filter is displayed as in menus.',
            },
            {
                'label': 'Source',
                'name': 'source_id',
                'type': 'select',
                'options': list(itertools.chain(
                    [{'name': f'{source_id}', 'label': f'Source: {name}'} for name, source_id in info['sources']],
                    [{'name': f'{filter_id}', 'label': f'Filter: {name}'} for name, filter_id in info['filters']],
                )),
                'default': config['source_id'],
                'tooltip': 'Source from which to receive data and print.',
            },
        ]
    def build(self, source_object, config):
        source_process = source_object.built_object
        if source_process is None:
            raise ValueError("Source needs to be built")

        if source_process.pub_address is None:
            raise AssertionError

        return GraphingFilterProcess(source_process.pub_address)



class GraphingFilterProcess:
    def __init__(self, source_pub_address):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        self.window = QtWidgets.QWidget()
        self.window.show()

        def setup(data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(source_pub_address)
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())


        def workload(data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                data['publisher'].send(item)
                logging.info(f'Filter printing: {item}')

        def cleanup(data):
            pipe_send.close()

        self._enabled = False
        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._pub_address = pipe_recv.recv()

    @property
    def pub_address(self):
        return self._pub_address

    @property
    def status(self):
        return 'enabled' if self._enabled else 'disabled'

    def enable(self):
        self._proc.start()
        self._enabled = True

    def disable(self):
        self._proc.pause()
        self._enabled = False

