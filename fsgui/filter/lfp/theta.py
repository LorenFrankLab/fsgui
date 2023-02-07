import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node
import json
import shapely


class ThetaFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Theta Filter',
            datatype='bool',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Theta filter',
                'source_id': None,
                'speedThresh': 2,
                'filterDelay': 730,
                'thetaPhase': 0,
                # 'mode': 'live',
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
                'type': 'node:float',
                'default': config['source_id'],
                'tooltip': 'Source to receive LFP data',
            },
            {
                'label': 'Speed threshold',
                'name': 'speedThresh',
                'type': 'double',
                'lower': 0,
                'upper': 100,
                'decimals': 2,
                'default': config['speedThresh'],
                'units': 'cm/s',
            },
            {
                'label': 'Filter Delay',
                'name': 'filterDelay',
                'type': 'integer',
                'lower': 0,
                'upper': 20000,
                'default': config['filterDelay'],
                'units': 'ms',
            },
            {
                'label': 'Desired phase of stimulation',
                'name': 'thetaPhase',
                'type': 'integer',
                'lower': 0,
                'upper': 360*4,
                'default': config['thetaPhase'],
                'units': 'deg',
            }
        ]
