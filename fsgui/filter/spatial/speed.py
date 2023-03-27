import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node


class SpeedFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Speed filter',
            datatype='bool',
            default=None
        )

    def write_template(self, config = None):
        config = config if config is not None else {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'source_id': None,
            'smooth_x': True,
            'smooth_y': True,
            'smooth_speed': False,
            'position_sampling_rate': 30,
            'scale_factor': 0.222,
            'threshold': 10.0,
            'threshold_above': False,
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
                'label': 'Source',
                'name': 'source_id',
                'type': 'node:point2d',
                'default': config['source_id'],
                'tooltip': 'Source to receive spatial data from',
            },
            {
                'label': 'Smooth x',
                'name': 'smooth_x',
                'type': 'boolean',
                'default': config['smooth_x'],
                'tooltip': 'Whether or not to smooth the x-positions using a filter.',
            },
            {
                'label': 'Smooth y',
                'name': 'smooth_y',
                'type': 'boolean',
                'default': config['smooth_y'],
                'tooltip': 'Whether or not to smooth the y-positions using a filter.',
            },
            {
                'label': 'Smooth speed',
                'name': 'smooth_speed',
                'type': 'boolean',
                'default': config['smooth_speed'],
                'tooltip': 'Whether or not to smooth the speed value using a filter.',
            },
            {
                'label': 'Sample rate',
                'name': 'position_sampling_rate',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'units': 'Hz',
                'default': config['position_sampling_rate'],
                'tooltip': 'Whether or not to smooth the speed value using a filter.',
            },
            {
                'label': 'Scale factor',
                'name': 'scale_factor',
                'type': 'double',
                'lower': 0,
                'upper': 1,
                'default': config['scale_factor'],
                'tooltip': 'The factor used to scale the speed into the units of the threshold.',
            },
            {
                'label': 'Threshold',
                'name': 'threshold',
                'type': 'double',
                'lower': 0,
                'upper': 100000000000,
                'decimals': 2,
                'default': config['threshold'],
                'tooltip': 'The speed threshold required to trigger the filter.',
            },
            {
                'label': 'Threshold above',
                'name': 'threshold_above',
                'type': 'boolean',
                'default': config['threshold_above'],
                'tooltip': 'True indicates the speed must be above the threshold to trigger. False indicates speed must be below threshold to trigger.',
            },
        ]

    def build(self, config, addr_map):
        pub_address = addr_map[config['source_id']]

        # weighting recent estimates more
        smoothing_filter = [0.31, 0.29, 0.25, 0.15]

        def setup(reporter, data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(pub_address)
            data['filter_model'] = KinematicsEstimator(
                scale_factor=config['scale_factor'],
                dt=1/config['position_sampling_rate'],
                xfilter=smoothing_filter,
                yfilter=smoothing_filter,
                speedfilter=smoothing_filter,
            )

        def workload(connection, publisher, reporter, data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                _, _, speed = data['filter_model'].compute_kinematics(
                    item['x'], item['y'],
                    smooth_x=config['smooth_x'],
                    smooth_y=config['smooth_y'],
                    smooth_speed=config['smooth_speed'],
                )

                if config['threshold_above']:
                    triggered = speed > config['threshold']
                else:
                    triggered = speed < config['threshold']
                
                # convert from numpy to Python bool
                triggered = bool(triggered)

                publisher.send(triggered)

        return fsgui.process.build_process_object(setup, workload)

class KinematicsEstimator(object):

    def __init__(
        self, *, scale_factor=1, dt=1,
        xfilter=None, yfilter=None,
        speedfilter=None
    ):
        self._sf = scale_factor
        self._dt = dt

        self._b_x = np.array(xfilter)
        self._b_y = np.array(yfilter)
        self._b_speed = np.array(speedfilter)

        self._buf_x = np.zeros(self._b_x.shape[0])
        self._buf_y = np.zeros(self._b_y.shape[0])
        self._buf_speed = np.zeros(self._b_speed.shape[0])

        self._last_x = -1
        self._last_y = -1
        self._last_speed = -1

    def compute_kinematics(
        self, x, y, *, smooth_x=False,
        smooth_y=False, smooth_speed=False
    ):

        # very first datapoint
        if self._last_speed == -1:
            self._last_x = x
            self._last_y = y
            self._last_speed = 0
            return x, y, 0

        if smooth_x:
            xv = self._smooth(x * self._sf, self._b_x, self._buf_x)
        else:
            xv = x

        if smooth_y:
            yv = self._smooth(y * self._sf, self._b_y, self._buf_y)
        else:
            yv = y

        sv = np.sqrt((yv - self._last_y)**2 + (xv - self._last_x)**2) / self._dt
        if smooth_speed:
            sv = self._smooth(sv, self._b_speed, self._buf_speed)

        # now that the speed has been estimated, the current x and y values
        # become the most recent (last) x and y values
        self._last_x = xv
        self._last_y = yv
        self._last_speed = sv

        return xv, yv, sv

    def _smooth(self, newval, coefs, buf):

        # mutates data!
        buf[1:] = buf[:-1]
        buf[0] = newval
        rv = np.sum(coefs * buf, axis=0)

        return rv