import ghostipy as gsp
import scipy.signal

import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node
import json
import time
import fsgui.nparray


class RippleFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Ripple filter (new)',
            datatype='bool',
        )

    def write_template(self, config = None):
        config = config if config is not None else {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'source_id': None,
            'num_signals': 32,
            'bp_order': 2,
            'bp_crit_freqs_low': 150,
            'bp_crit_freqs_high': 250,
            'lfp_sample_rate': 1500,
            'env_num_taps': 15,
            'env_band_edges_low': 50,
            'env_band_edges_high': 55,
            'sd_threshold': 3.5,
            'n_above_threshold': 1,
            'tetrode_selection': None,
            'display_channel': 1,
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
                'type': 'node:float',
                'default': config['source_id'],
                'tooltip': 'Source to receive LFP data',
            },
            {
                'label': 'Number of signals (e.g. 32 vs 64 tetrodes)',
                'name': 'num_signals',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['num_signals'],
            },
            {
                'label': 'Bandpass filter: order',
                'name': 'bp_order',
                'type': 'integer',
                'lower': 1,
                'upper': 100,
                'default': config['bp_order'],
                'tooltip': 'The order of the IIR filter used to bandpass the LFP data into a ripple band.',
            },
            {
                'label': 'Bandpass filter: low cut',
                'name': 'bp_crit_freqs_low',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'units': 'Hz',
                'default': config['bp_crit_freqs_low'],
                'tooltip': 'The low cut frequency of the IIR filter used to bandpass the LFP data into a ripple band.',
            },
            {
                'label': 'Bandpass filter: high cut',
                'name': 'bp_crit_freqs_high',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'units': 'Hz',
                'default': config['bp_crit_freqs_high'],
                'tooltip': 'The high cut frequency of the IIR filter used to bandpass the LFP data into a ripple band.',
            },
            {
                'label': 'LFP Sample rate (Hz)',
                'name': 'lfp_sample_rate',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['lfp_sample_rate'],
                'units': 'Hz',
                'tooltip': 'The sample rate of the LFP data.'
            },
            {
                'label': 'Envelope filter: number of taps',
                'name': 'env_num_taps',
                'type': 'integer',
                'lower': 1,
                'upper': 100,
                'units': 'taps',
                'default': config['env_num_taps'],
                'tooltip': 'The number of taps or weights in the FIR filter used to envelope the ripple band signal.',
            },
            {
                'label': 'Envelope filter: low cut',
                'name': 'env_band_edges_low',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'units': 'Hz',
                'default': config['env_band_edges_low'],
                'tooltip': 'The low cut frequency of the FIR filter used to envelope the ripple band signal.',
            },
            {
                'label': 'Envelope filter: high cut',
                'name': 'env_band_edges_high',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'units': 'Hz',
                'default': config['env_band_edges_high'],
                'tooltip': 'The high cut frequency of the FIR filter used to envelope the ripple band signal.',
            },
            {
                'label': 'Threshold',
                'name': 'sd_threshold',
                'type': 'double',
                'lower': 0,
                'upper': 100,
                'units': 'std',
                'decimals': 2,
                'default': config['sd_threshold'],
                'tooltip': 'The threshold in standard deviations that a channel has to reach in order to count as a ripple on the channel.',
            },
            {
                'label': 'Number of channels above threshold to trigger filter',
                'name': 'n_above_threshold',
                'type': 'integer',
                'lower': 0,
                'upper': 10000,
                'units': 'channels',
                'default': config['n_above_threshold'],
                'tooltip': 'The number of channels that need to have a ripple detected to trigger the filter.',
            },
            {
                'label': 'Tetrode selection',
                'name': 'tetrode_selection',
                'type': 'tetrode_selection',
                'default': config['tetrode_selection'],
            },
            {
                'label': 'Display channel (reporting graphics)',
                'name': 'display_channel',
                'type': 'integer',
                'lower': 1,
                'upper': 10000,
                'default': config['display_channel'],
                'tooltip': 'The channel to display in the reporting graphics view. Ignore if not using graphics.',
            },
 
        ]
    
    def build(self, config, pipe_map):
        source_pipe = pipe_map[config['source_id']]

        tetrodes = config['tetrode_selection']['tetrodes']
        if config['tetrode_selection']['is_include']:
            tetrode_ids = np.array(tetrodes) - 1
        else:
            tetrode_ids = np.setdiff1d(np.arange(config['num_signals']), np.array(tetrodes) - 1)
        num_signals = len(tetrode_ids)

        display_channel = config['display_channel']
        display_index = np.where(tetrode_ids == display_channel - 1)[0]

        rip_filter = EnvelopeEstimator(
            num_signals=num_signals,
            bp_order=config['bp_order'],
            bp_crit_freqs=[config['bp_crit_freqs_low'], config['bp_crit_freqs_high']],
            lfp_sampling_rate=config['lfp_sample_rate'],
            env_num_taps=config['env_num_taps'],
            env_band_edges=[config['env_band_edges_low'], config['env_band_edges_high']],
            # no point in changing this
            env_desired=[1,0],
        )

        def estimate_new_stats_welford(new_value, mean, M2, count):
            count += 1
            delta = (new_value - mean)
            mean += delta / count
            delta2 = (new_value - mean)
            M2 += (delta*delta2)
            return mean, M2, count

        def setup(logging, data):
            data['filter_model'] = rip_filter
            data['means'] = np.zeros(num_signals)
            data['M2'] = np.zeros(num_signals)
            data['counts'] = np.zeros(num_signals)
            data['sigmas'] = np.zeros(num_signals)
            data['update_stats'] = True

        def workload(connection, publisher, reporter, data):
            if source_pipe.poll(timeout=1):
                item = source_pipe.recv()

                lfps = np.array(item['lfpData'])[tetrode_ids]
                ripple_data, envelope = data['filter_model'].add_new_data(lfps)

                if data['update_stats']:
                    # updates stats
                    data['means'], data['M2'], data['counts']= estimate_new_stats_welford(
                        envelope, data['means'], data['M2'], data['counts']
                    )
                    data['sigmas'] = np.sqrt(data['M2'] / data['counts'])

                z_score_envelope = (envelope - data['means']) / data['sigmas']
                n_detected = np.sum(z_score_envelope > config['sd_threshold'])
                triggered = n_detected >= config['n_above_threshold']

                # convert from numpy type to Python type
                triggered = bool(triggered)
                publisher.send(triggered)

                reporter.send({
                    'triggered': triggered,
                    'raw_lfp_value': lfps[display_index],
                    'ripple_data': ripple_data[display_index],
                    'envelope': envelope[display_index],
                })

        return fsgui.process.build_process_object(setup, workload)
    

class EnvelopeEstimator:
    def __init__(self, num_signals, bp_order=2, bp_crit_freqs=[150,250], lfp_sampling_rate=1500, env_num_taps=15, env_band_edges=[50,55], env_desired=[1,0]):
        # set up iir
        sos = scipy.signal.iirfilter(
            bp_order,
            bp_crit_freqs,
            output='sos',
            fs=lfp_sampling_rate,
            btype='bandpass',
            ftype='butter',
        )[:, :, None]

        ns = sos.shape[0]
        self._b_ripple = sos[:, :3] # (ns, 3, num_signals)
        self._a_ripple = sos[:, 3:] # (ns, 3, num_signals)

        self._x_ripple = np.zeros((ns, 3, num_signals))
        self._y_ripple = np.zeros((ns, 3, num_signals))

        # set up envelope filter
        self._b_env = gsp.firdesign(
            env_num_taps,
            env_band_edges,
            env_desired,
            fs=lfp_sampling_rate,
        )[:, None]
        self._x_env = np.zeros((self._b_env.shape[0], num_signals))

    def add_new_data(self, data):
        # coming in parallel, data has width of num_signals

        # IIR ripple bandpass
        ns = self._a_ripple.shape[0]
        for ii in range(ns):

            self._x_ripple[ii, 1:] = self._x_ripple[ii, :-1]
            if ii == 0: # new input is incoming data
                self._x_ripple[ii, 0] = data
            else: # new input is IIR output of previous stage
                self._x_ripple[ii, 0] = self._y_ripple[ii - 1, 0]

            self._y_ripple[ii, 1:] = self._y_ripple[ii, :-1]
            ripple_data = (
                np.sum(self._b_ripple[ii] * self._x_ripple[ii], axis=0) -
                np.sum(self._a_ripple[ii, 1:] * self._y_ripple[ii, 1:], axis=0)
            )
            self._y_ripple[ii, 0] = ripple_data
        

        # FIR estimate envelope
        self._x_env[1:] = self._x_env[:-1]
        self._x_env[0] = ripple_data**2
        # parallel dot product without saying it's a dot product
        env = np.sqrt(np.sum(self._b_env * self._x_env, axis=0))

        return ripple_data, env

