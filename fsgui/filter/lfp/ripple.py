import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node
import json
import shapely


class RippleFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Ripple filter',
            datatype='bool',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Ripple filter',
                'source_id': None,
                'sampleDivisor': 10000,
                'ripCoeff1': 1.2,
                'ripCoeff2': 0.2,
                'ripThresh': 5,
                'nAboveThresh': 1,
                'lockoutTime': 7500,
                'detectNoRipples': False,
                'detectNoRipplesTime': 60000,
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
                'label': 'Sample Divisor',
                'name': 'sampleDivisor',
                'type': 'integer',
                'lower': 0,
                'upper': 1000000,
                'default': config['sampleDivisor'] 
            },
            {
                'label': 'Rip. Coeff 1',
                'name': 'ripCoeff1',
                'type': 'double',
                'lower': 0,
                'upper': 2,
                'decimals': 3,
                'default': config['ripCoeff1'],
            },
            {
                'label': 'Rip. Coeff 2',
                'name': 'ripCoeff2',
                'type': 'double',
                'lower': 0,
                'upper': 2,
                'decimals': 3,
                'default': config['ripCoeff2'],
            },
            {
                'label': 'Ripple Threshold (sd)',
                'name': 'ripThresh',
                'type': 'double',
                'lower': 0,
                'upper': 20,
                'decimals': 2,
                'default': config['ripThresh'],
            },
            {
                'label': 'Num Above Threshold',
                'name': 'nAboveThresh',
                'type': 'integer',
                'lower': 0,
                'upper': 128,
                'default': config['nAboveThresh']
            },
            {
                'label': 'Lockout period (timestamps)',
                'name': 'lockoutTime',
                'type': 'integer',
                'lower': 0,
                'upper': 30000,
                'default': config['lockoutTime']
            },
            {
                'label': 'Detect Ripple Absence',
                'name': 'detectNoRipples',
                'type': 'boolean',
                'default': config['detectNoRipples']
            },
            {
                'label': 'No ripples window length (timestamps)',
                'name': 'detectNoRipplesTime',
                'type': 'integer',
                'lower': 0,
                'upper': 300000,
                'default': config['detectNoRipplesTime']
            },
        ]
