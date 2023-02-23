import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node
import json
import shapely

class AxisAlignedRectangleFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Axis-aligned rectangle filter',
            datatype='bool',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Axis-aligned rectangle filter',
                'source_id': None,
                'lowerLeftX': 0,
                'lowerLeftY': 0,
                'upperRightX': 0,
                'upperRightY': 0,
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
                'label': 'Lower Left (X)',
                'name': 'lowerLeftX',
                'type': 'integer',
                'lower': 0,
                'upper': 2000,
                'default': config['lowerLeftX'],
                'units': 'pixels',
            },
            {
                'label': 'Lower Left (Y)',
                'name': 'lowerLeftY',
                'type': 'integer',
                'lower': 0,
                'upper': 2000,
                'default': config['lowerLeftY'],
                'units': 'pixels',
            },
            {
                'label': 'Upper Right (X)',
                'name': 'upperRightX',
                'type': 'integer',
                'lower': 0,
                'upper': 2000,
                'default': config['upperRightX'],
                'units': 'pixels',
            },
            {
                'label': 'Upper Right (Y)',
                'name': 'upperRightY',
                'type': 'integer',
                'lower': 0,
                'upper': 2000,
                'default': config['upperRightY'],
                'units': 'pixels',
            },
       ]

    def build(self, config, addr_map):
        pub_address = addr_map[config['source_id']]
        
        lower_left = config['lowerLeftX'], config['lowerLeftY']
        upper_right = config['upperRightX'], config['upperRightY']

        def setup(reporter, data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(pub_address)
            data['filter_model'] = AxisAlignedRectangleFilter(lower_left, upper_right)

        def workload(connection, publisher, reporter, data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                x, y = tuple(map(float, item.split(',')))
                triggered = data['filter_model'].check_bounds(x, y)
                publisher.send(f'{triggered}')

        return fsgui.process.build_process_object(setup, workload)

class AxisAlignedRectangleFilter:
    def __init__(self, lower_left, upper_right, inclusive=True):
        self._lower_left = lower_left
        self._upper_right = upper_right

        if inclusive:
            self.check_bounds = self.__check_bounds_inclusive
        else:
            self.check_bounds = self.__check_bounds_exclusive
    
    def __check_bounds_inclusive(self, x, y):
        return x >= self._lower_left[0] and x <= self._upper_right[1] and y >= self._lower_left[1] and y <= self._upper_right[1]

    def __check_bounds_exclusive(self, x, y):
        return x > self._lower_left[0] and x < self._upper_right[1] and y > self._lower_left[1] and y < self._upper_right[1]
