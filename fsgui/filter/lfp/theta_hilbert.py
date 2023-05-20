import multiprocessing as mp
import numpy as np
import fsgui.process
import fsgui.node
import json
import logging

import fsgui.nparray
import scipy.signal
import time

class ThetaPhaseHilbertFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name='Theta filter (Hilbert phase)',
            datatype='bool',
       )

    def write_template(self, config = None):
        config = config if config is not None else {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'source_id': None,
            'theta_filter_degrees': 0,
            'reference_ntrode': 0,
            'lfp_sample_rate': 1500,
            'timestamp_interval': 20,
            'trim_proportion': 0.15,
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
                'label': 'Theta phase of stimulation',
                'name': 'theta_filter_degrees',
                'type': 'integer',
                'lower': 0,
                'upper': 360,
                'default': config['theta_filter_degrees'],
                'units': 'deg',
            },
            {
                'label': 'Reference tetrode id',
                'name': 'reference_ntrode',
                'type': 'integer',
                'lower': 0,
                'upper': 20000,
                'default': config['reference_ntrode'],
                'tooltip': 'The ntrode to use as the reference to calculate theta filter on.',
            },
            {
                'label': 'LFP Sample rate (Hz)',
                'name': 'lfp_sample_rate',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['lfp_sample_rate'],
                'units': 'Hz',
            },
            {
                'label': 'Timestamp interval (from hardware)',
                'name': 'timestamp_interval',
                'type': 'integer',
                'lower': 0,
                'upper': 2000,
                'default': config['timestamp_interval'],
                'units': 'timestamps'
            },
            {
                'label': 'Autoregression model trim proportion',
                'name': 'trim_proportion',
                'type': 'double',
                'lower': 0,
                'upper': 1,
                'default': config['trim_proportion'],
            },
        ]

    def build(self, config, pipe_map):
        source_pipe = pipe_map[config['source_id']]

        theta_filter = ThetaHilbertYuleWalkerFilter(
            phase_deg=config['theta_filter_degrees'],
            samples_per_second=config['lfp_sample_rate'],
            timestamp_interval=config['timestamp_interval'],
            trim_proportion=config['trim_proportion'],
        )

        tetrode_id=config['reference_ntrode']

        def setup(logging, data):
            data['filter_model'] = theta_filter
            data['last_known_theta_val'] = 0

        def workload(connection, publisher, reporter, data):
            if source_pipe.poll(timeout=1):
                item = source_pipe.recv()
                lfpVal=item['lfpData'][tetrode_id]
                sampleTime=item['localTimestamp']

                triggered, theta_val = data['filter_model'].process_theta_data(lfpVal, sampleTime)

                if theta_val is None:
                    theta_val = data['last_known_theta_val']
                else:
                    data['last_known_theta_val'] = theta_val

                publisher.send(triggered)
                reporter.send({
                    'trig': triggered,
                    'theta_val': theta_val,
                })

        return fsgui.process.build_process_object(setup, workload)

class FirstOrderButterworthThetaFilter:
    def __init__(self, sample_rate, lowcut=4.0, highcut=9.0):
        self.sample_rate = sample_rate
        self.lowcut = lowcut
        self.highcut = highcut

        order=1
        self.theta_num, self.theta_denom = scipy.signal.butter(
            N=order,
            Wn=[lowcut,highcut],
            btype='bandpass',
            output='ba',
            fs=self.sample_rate
        )
    
    def filter_signal(self, signal):
        return scipy.signal.filtfilt(self.theta_num, self.theta_denom, signal)

class ARForwardPredictor:
    def __init__(self, ar_params, input_length, n_future_samples):
        self.ar_params = ar_params
        self.order = len(self.ar_params)

        self.weights = np.empty((self.order, self.order + n_future_samples))
        for t in range(self.order):
            self.weights[:,t] = 0
            self.weights[t,t] = 1
        for t in range(self.order, self.order+n_future_samples):
            for j in range(self.order):
                self.weights[j,t] = np.dot(np.flip(self.ar_params), self.weights[j, t-self.order:t])

        self.full_buffer = np.empty((input_length + n_future_samples,))
    
    def forward_predict_ar(self, input_signal):
        self.full_buffer[:len(input_signal)] = input_signal
        self.full_buffer[len(input_signal):] = np.matmul(input_signal[-self.order:], self.weights)[self.order:]
        return self.full_buffer

class ThetaHilbertYuleWalkerFilter:
    def __init__(self, phase_deg = 90, samples_per_second = 1500, timestamp_interval = 20, trim_proportion = 0.15):
        self.sample_rate = samples_per_second
        self.trim_n_samples = int(self.sample_rate * trim_proportion)
        self.timestamp_interval = timestamp_interval

        # create buffers
        self.buffer_length = self.sample_rate * 1
        self.lfp_buffer = fsgui.nparray.CircularArray(length=self.buffer_length)
        self.time_buffer = fsgui.nparray.CircularArray(length=self.buffer_length)

        # we assume a negative cosine wave for phase based on old FSGui conventions
        assert phase_deg >= 0 and phase_deg <= 360
        self.phase_rad = ((phase_deg + 180) % 360) / 360.0 * 2 * np.pi

        self.theta_filter = FirstOrderButterworthThetaFilter(self.sample_rate)

        self.ar_params = [
            1.08533899e+00,
            -1.64429982e-03,
            -1.63323224e-03,
            -1.59761023e-03,
            -1.53600881e-03,
            -1.44889199e-03,
            -1.33853721e-03,
            -1.20873293e-03,
            -1.06429170e-03,
            -9.10446360e-04,
            -7.52213166e-04,
            -5.93809632e-04,
            -7.72185455e-02
        ]

        self.ar_predictor = ARForwardPredictor(self.ar_params, self.buffer_length - 2 * self.trim_n_samples, 2 * self.trim_n_samples)

        self.next_trigger_estimate = None

    def __trim_both_edges(self, signal):
        return signal[self.trim_n_samples:-self.trim_n_samples]

    def process_theta_data(self, lfpVal, sampleTime):
        # place data and get lfp buffer
        self.lfp_buffer.place(lfpVal)
        self.time_buffer.place(sampleTime)

        if self.next_trigger_estimate is not None:
            if self.next_trigger_estimate <= sampleTime:
                self.next_trigger_estimate = None
                return True, None
            else:
                return False, None
        else:
            lfp_data = np.flip(self.lfp_buffer.get_slice)
            lfp_data_ts = np.flip(self.time_buffer.get_slice)

            # filter data
            theta_data = self.theta_filter.filter_signal(lfp_data)

            # trim off the edge effects
            theta_trim = self.__trim_both_edges(theta_data)
            theta_trim_ts = self.__trim_both_edges(lfp_data_ts)

            # theta_predicted, theta_predicted_ts = self.__forward_predict_ar(theta_trim, theta_trim_ts, n_future_samples=2*self.trim_n_samples)
            theta_predicted = self.ar_predictor.forward_predict_ar(theta_trim)
            theta_predicted_ts = np.hstack([theta_trim_ts, [theta_trim_ts[-1] + 20 * (i+1) for i in range(2*self.trim_n_samples)]])

            analytic_signal = scipy.signal.hilbert(theta_predicted)
            instantaneous_phase = np.unwrap(np.angle(analytic_signal))

            # calculate unwrapped target phase
            phase_point_estimate = instantaneous_phase[-self.trim_n_samples]
            local_phase = phase_point_estimate % (2*np.pi)
            next_target_phase = phase_point_estimate + (self.phase_rad - local_phase) % (2*np.pi)

            # at which point will the phase equal our target phase
            phase_array_index = np.searchsorted(instantaneous_phase, next_target_phase)
            future_relative_index = phase_array_index - len(lfp_data_ts) + self.trim_n_samples

            # avoid setting next estimate too close or too far into the future
            if self.trim_n_samples / 4 < future_relative_index and future_relative_index < self.trim_n_samples / 2:
                self.next_trigger_estimate = lfp_data_ts[-1] + self.timestamp_interval * (future_relative_index)

            return False, theta_data[-1]
