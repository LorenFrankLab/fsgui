import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node
import json
import shapely

class SpeedFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Speed filter',
            datatype='bool',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Speed filter',
                'source_id': None,
                'cmPerPix': 0.20,
                'minSpeed': 0,
                'maxSpeed': 500,
                'lockoutTime': 7500,
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
                'label': 'Source',
                'name': 'source_id',
                'type': 'node:point2d',
                'default': config['source_id'],
                'tooltip': 'Source to receive spatial data from',
            },
            {
                'label': 'Centimeters per pixel',
                'name': 'cmPerPix',
                'type': 'double',
                'lower': 0,
                'upper': 10,
                'default': config['cmPerPix'],
                'decimals': 2,
                'units': 'cm/pixel',
            },
            {
                'label': 'Minimum speed',
                'name': 'minSpeed',
                'type': 'double',
                'default': config['minSpeed'],
                'lower': -1,
                'upper': 200.0,
                'decimals': 2,
                'units': 'cm/sec'
            },
            {
                'label': 'Maximum speed',
                'name': 'maxSpeed',
                'type': 'double',
                'lower': 0,
                'upper': 1000,
                'default': config['maxSpeed'],
                'decimals': 2,
                'units': 'cm/sec'
            },
            {
                'label': 'Min On/Off Length',
                'name': 'lockoutTime',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['lockoutTime'],
                'units': 'timestamps'
            },
        ]

    def build(self, config, addr_map):
        source_id = config['source_id']
        pub_address = addr_map[source_id]
        return SpeedFilterProcess(pub_address)

class SpeedFilterProcess:
    def __init__(self, source_pub_address):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(source_pub_address)
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())
            data['filter_model'] = SpeedFilter()

        def workload(data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                x, y = tuple(map(float, item.split(',')))
                triggered = data['filter_model'].check_speed(x, y)
                data['publisher'].send(f'{triggered}')

        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()
        self.pub_address = pipe_recv.recv()

class SpeedFilter:
    def __init__(self):
        pass

    def check_speed(self, x, y):
        import logging
        logging.info(f'{x} {y}')

        return True


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
