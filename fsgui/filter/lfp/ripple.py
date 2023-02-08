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

class RippleFilterCoefficients19:
    def __init__(self):
        self.length = 19
        self.numerator = np.array([
            2.435723358568172431e-02,
            -1.229133831328424326e-01,
            2.832924715801946602e-01,
            -4.629092463232863941e-01,
            6.834398182647745124e-01,
            -8.526143367711925825e-01,
            8.137704425816699727e-01,
            -6.516133270563613245e-01,
            4.138371933419512372e-01,
            2.165520280363200556e-14,
            -4.138371933419890403e-01,
            6.516133270563868596e-01,
            -8.137704425816841836e-01,
            8.526143367711996879e-01,
            -6.834398182647782871e-01,
            4.629092463232882815e-01,
            -2.832924715801954929e-01,
            1.229133831328426407e-01,
            -2.435723358568174512e-02,
        ])
        self.denominator = np.array([
            1.000000000000000000e+00,
            -7.449887056735371438e+00,
            2.866742370538527496e+01,
            -7.644272470167831557e+01,
            1.585893197862293391e+02,
            -2.703338821178639932e+02,
            3.898186201116285474e+02,
            -4.840217978093359079e+02,
            5.230782138295531922e+02,
            -4.945387299274730140e+02,
            4.094389697124813665e+02,
            -2.960738943482194827e+02,
            1.857150345772943751e+02,
            -9.980204002570326338e+01,
            4.505294594295533273e+01,
            -1.655156422615593215e+01,
            4.683913633549676270e+00,
            -9.165841559639211766e-01,
            9.461443242601841330e-02,
        ])

class RippleFilterParams:
    def __init__(self, ripCoeff1, ripCoeff2, ripple_threshold, sampDivisor, n_above_thresh, lockoutTime, detectNoRippleTime, dioGatePort, detectNoRipples, dioGate, enabled, useCustomBaseline, updateCustomBaseline):
        self.ripCoeff1 = ripCoeff1
        self.ripCoeff2 = ripCoeff2
        self.ripple_threshold = ripple_threshold
        self.sampDivisor = sampDivisor
        self.n_above_thresh = n_above_thresh
        self.lockoutTime = lockoutTime
        self.detectNoRippleTime = detectNoRippleTime
        self.dioGatePort = dioGatePort
        self.detectNoRipples = detectNoRipples
        self.dioGate = dioGate
        self.enabled = enabled
        self.useCustomBaseline = useCustomBaseline
        self.updateCustomBaseline = updateCustomBaseline

class RippleFilter:
    def __init__(self, num_tetrodes, coefficients, params, num_last_values=20):
        self.num_tetrodes = num_tetrodes
        self.coefficients = coefficients
        self.params = params
        self.num_last_values = num_last_values
        
        # tetrode-specific data
        self.rippleMean = np.zeros(shape=(num_tetrodes,), dtype='double')
        self.rippleSd = np.zeros(shape=(num_tetrodes,), dtype='double')

        self.f_x = np.zeros(shape=(num_tetrodes, self.coefficients.length), dtype='double')
        self.f_y = np.zeros(shape=(num_tetrodes, self.coefficients.length), dtype='double')
        self.filtind = np.zeros(shape=(num_tetrodes,), dtype='int')

        self.last_vals = np.zeros(shape=(num_tetrodes, self.num_last_values), dtype='double')
        self.lvind = np.zeros(shape=(num_tetrodes,), dtype='int')
        self.current_val = np.zeros(shape=(num_tetrodes,), dtype='double')

        self.n_trode_id = np.zeros(shape=(num_tetrodes,), dtype='int')
        self.enabled = np.zeros(shape=(num_tetrodes,), dtype='bool')

    def reset_ripple_data(self):
        self.rippleMean[:] = 0
        self.rippleSd[:] = 0
        self.f_x[:,:] = 0
        self.f_y[:,:] = 0
        self.filtind[:] = 0
        self.last_vals[:,:] = 0
        self.lvind[:] = 0
        self.current_val[:] = 0
    
    def reset_counter(self):
        self.counter = 0

    def update_last_val(self, ntrodeid, value):
        """
        updates last_val and advances last_val index
        """
        mean = np.mean(self.last_vals[ntrodeid,:])
        self.last_vals[ntrodeid, self.lvind[ntrodeid]] = value

        # advance circular index
        self.lvind[ntrodeid] += 1
        self.lvind[ntrodeid] %= self.num_last_values
        return mean

    def filter_channel(self, ntrodeid, d):
        """
        updates f_x, f_y and advances filter index
        """
        self.f_x[ntrodeid, self.filtind[ntrodeid]] = d
        self.f_y[ntrodeid, self.filtind[ntrodeid]] = 0
        shift = self.filtind[ntrodeid]
        val = np.dot(np.roll(self.f_x[ntrodeid, :], -shift), self.coefficients.numerator) - np.dot(np.roll(self.f_y[ntrodeid, :], -shift), self.coefficients.denominator)
        self.f_y[ntrodeid, self.filtind[ntrodeid]] = val

        # advance circular index
        self.filtind[ntrodeid] -= 1
        self.filtind[ntrodeid] %= self.coefficients.length
        return val

    def process_ripple_data(self, ntrodeid, d, calculate_v, run_update_mean_sd=True, run_calculate_v=True):
        """
        d: the input signal, which could be linearly ramped during lockout

        run_update_mean_and_sd: this flag should be false during artifacts (i.e. during stimulation)
            only update the mean and sd if not stimulating
            this stops the stimulation artifact from changing values
        run_calculate_v: this flag should be false for the first 10k samples startup or when in lockout
            v is roughly the envelope of the ripple magnitude
        """

        rd = self.filter_channel(ntrodeid, d)

        magnitude_rd = np.abs(rd)

        if run_update_mean_sd:
            self.update_mean_sd(ntrodeid, magnitude_rd)

        if run_calculate_v:
            self.current_val[ntrodeid] = self.calculate_v(ntrodeid, magnitude_rd)
        else:
            self.current_val[ntrodeid] = self.rippleMean[ntrodeid]

        return self.count_above_threshold() >= self.params.n_above_thresh

    def update_mean_sd(self, ntrodeid, ripple_signal):
        """
        ripple_signal: the absolute value of the ripple filtered
        """
        diff = ripple_signal - self.rippleMean[ntrodeid]
        self.rippleMean[ntrodeid] += diff / self.params.sampleDivisor
        self.rippleSd[ntrodeid] += (abs(diff) - self.rippleSd[ntrodeid]) / self.params.sampleDivisor

    def calculate_v(self, ntrodeid, ripple_signal):
        df = ripple_signal - self.current_val[ntrodeid]
        if df > 0:
            gain = self.update_last_val(ntrodeid, self.params.ripCoeff1)
        else:
            gain = self.params.ripCoeff2
            self.update_last_val(ntrodeid, gain)
        
        return self.current_val[ntrodeid] + df * gain
        
    def count_above_threshold(self):
        if self.params.useCustomBaseline:
            mean = None
            sd = None
            raise NotImplementedError('custom baseline is not implemented')
        else:
            mean = self.rippleMean
            sd = self.rippleSd
        
        threshold = mean + self.params.ripple_threshold * sd

        return np.sum((self.current_val > threshold)*self.enabled)
        
