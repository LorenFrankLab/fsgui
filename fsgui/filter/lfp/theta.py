import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node

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

class ThetaFilterParams:
    def __init__(self, targetPhase):
        self.targetPhase = targetPhase

class ThetaFilterCoefficientsDefault:
    def __init__(self):
        self.length = 3
        self.numerator = np.array([
            0.0165,
            0.0,
            -0.0165,
        ], dtype='double')
        self.denominator = np.array([
            1,
            -1.9662,
            0.9670,
        ], dtype='double')

class ThetaFilter:
    def __init__(self, coefficients):
        self.coefficients = coefficients

        # current filter state
        self.z = np.zeros(shape=(self.coefficients.length,), dtype='double')
        
        # The last filtered LFP value
        self.fLFPLast = 0

        # the time of the last upward going zero crossing
        self.upZeroCrossLast = -1e100
        # the current estimate of the period in seconds
        self.periodEstimate = 1e100

        # time, in seconds, for next stimulation
        self.nextTrigger = None

        # this is using a negative cosine wave as reference
        if self.params.targetPhase < 90:
            self.useUpCross = False
            self.degFromZeroCross = self.params.targetPhase + 90
        elif self.params.targetPhase >= 90 and self.params.targetPhase < 270:
            self.useUpCross = True
            self.degFromZeroCross = self.params.targetPhase - 90
        elif self.params.targetPhase >= 270:
            self.useUpCross = False
            self.degFromZeroCross = self.params.targetPhase - 270
        else:
            raise ValueError(f'Invalid target phase: {self.params.targetPhase}')

    def filter_data(self, lfp):
        fLFP = self.coefficients.numerator[0] * lfp + self.z[0]
        for i in range(1, self.coefficients.length):
            # update the filter state for the next iteration
            self.z[i-1] = self.coefficients.numerator[i] * lfp + self.z[i] - self.coefficients.denominator[i]*fLFP
        return fLFP
    
    def process_theta_data(lfpVal, sampleTime):
        fLFPCurrent = self.filter_data(lfpVal)

        if fLFPCurrent >= 0 and self.fLFPLast < 0:
            # signal rising edge, zero crossing
            upZeroCross = sampleTime
            self.periodEstimate = upZeroCross - self.upZeroCrossLast
            if self.useUpCross:
                self.nextTrigger = sampleTime + (self.degFromZeroCross/360.0)*self.periodEstimate
            self.upZeroCrossLast = upZeroCross
        elif fLFPCurrent <= 0 and self.fLFPLast > 0:
            if not self.useUpCross:
                self.nextTrigger = sampleTime + (self.degFromZeroCross/360.0)*self.periodEstimate
        
        self.fLFPLast = fLFPCurrent

        if self.nextTrigger is not None:
            return self.nextTrigger <= sampleTime
        else:
            return False
