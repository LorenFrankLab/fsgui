import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import fsgui.spikegadgets.action.shortcut
import functools
import operator
import time

class DigitalPulseWaveActionType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        super().__init__(
            type_id=type_id,
            node_class='action',
            name='Digital Pulsetrain',
            datatype=None,
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Digital Pulsetrain',
                'filter_id': None,
                'pulseLength': 1,
                'nPulses': 1,
                'preDelay': 0,
                'sequencePeriod': 100,
                'sequenceFrequency': 10,
                'autoSettle': True,
                'nOutputTrains': 1,
                'trainInterval': 1000,
                'primaryBit': 1,
                'biphasic': False,
                'secondaryBit': 1,
                'lockout_time': 0,
                'functNum': 0,
            }
        )

        self.network_location = network_location

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
                'label': 'Filter',
                'name': 'filter_id',
                'type': 'node:tree',
                'default': config['filter_id'],
                'tooltip': 'Filter on which to trigger our action',
            },
            {
                'label': 'Pulse length',
                'name': 'pulseLength',
                'type': 'integer',
                'lower': 1,
                'upper': 500,
                'default': config['pulseLength'],
                'units': 'ms',
                'tooltip': 'Length in milliseconds of each pulse in pulse sequence.'
            },
            {
                'label': '# of Pulses',
                'name': 'nPulses',
                'type': 'integer',
                'lower': 0,
                'upper': 10000,
                'default': config['nPulses'],
                'tooltip': 'Number of pulses in pulse sequence.'
            },
            {
                'label': 'Pre Delay',
                'name': 'preDelay',
                'type': 'integer',
                'lower': 0,
                'upper': 1000,
                'default': config['preDelay'],
                'units': 'ms',
                'tooltip': 'Time before first pulse',
            },
            {
                'label': 'Period',
                'name': 'sequencePeriod',
                'type': 'integer',
                'lower': 1,
                'upper': 5000,
                'decimals': 0,
                'default': config['sequencePeriod'],
                'units': 'ms',
                'tooltip': 'Period of pulses in pulse sequence.',
            },
            {
                'label': 'Number of output trains',
                'name': 'nOutputTrains',
                'type': 'integer',
                'lower': 0,
                'upper': 200,
                'default': config['nOutputTrains'],
                'tooltip': 'Number of output sequences to trigger before returning; Set to 0 for continuous trains',
                'special': 'Inf.',
            },
            {
                'label': 'Inter-train Interval',
                'name': 'trainInterval',
                'type': 'integer',
                'lower': 100,
                'upper': 60000,
                'default': config['trainInterval'],
                'units': 'ms',
                'tooltip': 'Time in milliseconds from the onset of one pulse/pulse sequence to the onset of the next.',
            },
            {
                'label': 'Primary pin',
                'name': 'primaryBit',
                'type': 'integer',
                'lower': 1,
                'upper': 64,
                'default': config['primaryBit'],
                'tooltip': 'Output pin (range 1 - 64) to stimulate. For biphasic triggering, this is the first pin '
                           'triggered.', 
            },
            {
                'label': 'Lockout time',
                'name': 'lockout_time',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['lockout_time'],
                'tooltip': 'Time in milliseconds to wait before triggering again.',
            },
            {
                'label': 'Function number',
                'name': 'functNum',
                'type': 'integer',
                'lower': 0,
                'upper': 32,
                'default': config['functNum'],
                'tooltip': 'StateScript function number to run.',
            },
        ]
    
    def __generate_statescript(self, function_num, pre_delay,
                              n_pulses, n_trains,
                              train_interval, sequence_period, primary_stim_pin, pulse_length):
        """
        This script was copied and translated from StimConfigureWidget::generateStateScript. The original logic is
        from 2015.

        This may need to be edited in order to include biphasic stimulation. In the case that we want to generate more
        complex code.

        Example output:
        ```
        int f11go
        int f11PulseCounter = 1
        int f11TrainCounter = 1;
        int f11LockOut = 0;
        function 11
          if (f11LockOut == 0) do
            f11LockOut = 1
            f11go = 1
            f11PulseCounter = 1
            f11TrainCounter = 1
            if f11go == 1 do in 3
              while f11go == 1 && f11TrainCounter <= 7 do every 13
                while f11go == 1 && f11PulseCounter <= 5 do every 17
                  portout[19]=1
                  do in 23
                    portout[19]=0
                  end
                  f11PulseCounter = f11PulseCounter + 1
                then do
                  f11PulseCounter = 1
                  f11TrainCounter = f11TrainCounter + 1
                end
              then do
                f11PulseCounter = 1
                f11TrainCounter = 1
              end
            end
            f11LockOut = 0
          end
        end;

        function 12
          f11go = 0
        end;
        ```
        """
        stop_function_num = function_num+1
        go_var = f'f{function_num}go'
        pulse_counter_var = f'f{function_num}PulseCounter'
        train_counter_var = f'f{function_num}TrainCounter'
        lockout_var = f'f{function_num}LockOut'

        go_check = f'{go_var} == 1'

        # declare spaces
        s2 = '  '
        s4 = s2*2
        s6 = s2*3
        s8 = s2*4
        s10 = s2*5
        s12 = s2*6
        endl = '\n'

        script = ""
        script += f'int {go_var}' + endl

        # declare and init pulse & train counters and lockout
        # not sure why there is no semicolon on the first one
        script += f'int {pulse_counter_var} = 1' + endl
        script += f'int {train_counter_var} = 1;' + endl
        script += f'int {lockout_var} = 0;' + endl

        script += f'function {function_num}' + endl
        script += s2 + f'if ({lockout_var} == 0) do' + endl
        script += s4 + f'{lockout_var} = 1' + endl
        script += s4 + f'{go_var} = 1' + endl
        script += s4 + f'{pulse_counter_var} = 1' + endl
        script += s4 + f'{train_counter_var} = 1' + endl

        if pre_delay == 0:
            script += s4 + f'if {go_check} do' + endl
        else:
            script += s4 + f'if {go_check} do in {pre_delay}' + endl

        # set the number of trains if we're not doing continuous pulses
        if n_pulses != 0:
            if n_trains != 0:
                script += s6 +f'while {go_check} && {train_counter_var} <= {n_trains} do every {train_interval}' + endl
            else:
                # otherwise we want continuous pulse trains, so we use 1 as the check value and skip incrementing the counter below
                # we only do this if we're not doing continuous pulses
                script += s6 + f'while {go_check} && {train_counter_var} <= {1} do every {train_interval}' + endl
            script += s8 + f'while {go_check} && {pulse_counter_var} <= {n_pulses} do every {sequence_period}' + endl
        else:
            script += s8 + f'while {go_check}&& {pulse_counter_var} <= {1} do every {sequence_period}' + endl

        script += s10 + f'portout[{primary_stim_pin}]=1' + endl

        script += s10 + f'do in {pulse_length}' + endl;
        script += s12 + f'portout[{primary_stim_pin}]=0' + endl
        script += s10 + 'end' + endl

        # increment the counter unless the value is 0, which corresponds to continuous (infinite) pulses
        if n_pulses != 0:
            script += s10 + f'{pulse_counter_var} = {pulse_counter_var} + 1' + endl

        script += s8 + 'then do' + endl
        script += s10 + f'{pulse_counter_var} = 1' + endl

        # increment the train counter unless the value is 0, which corresponds to continuous (infinite) pulses
        if n_pulses != 0 and n_trains != 0:
            script += s10 + f'{train_counter_var} = {train_counter_var} + 1' + endl
        script += s8 + 'end' + endl

        # we need to end the TrainCounter while loop
        if n_pulses != 0:
            script += s6 + 'then do' + endl
            script += s8 + f'{pulse_counter_var} = 1' + endl
            script += s8 + f'{train_counter_var} = 1' + endl
            script += s6 + 'end' + endl

        # end the second if
        script += s4 + 'end' + endl
        # reset the lock out
        script += s4 + f'{lockout_var} = 0' + endl
        # end the first if
        script += s2 + 'end' + endl

        script += 'end;' + endl

        # declare the stop function
        script += endl
        script += f'function {stop_function_num}' + endl
        script += s2 + f'{go_var} = 0' + endl
        script += 'end;' + endl

        return script
    
    def build(self, config, address_map):
        funct_num = config['functNum']

        script = self.__generate_statescript(
            function_num=funct_num,
            pre_delay=config['preDelay'],
            n_pulses=config['nPulses'],
            n_trains=config['nOutputTrains'],
            train_interval=config['trainInterval'],
            sequence_period=config['sequencePeriod'],
            primary_stim_pin=config['primaryBit'],
            pulse_length=config['pulseLength']
        )

        # send the script
        consumer = trodesnetwork.ServiceConsumer('statescript.service', server_address = f'{self.network_location.address}:{self.network_location.port}')
        consumer.request({
            'command': script,
        })

        sub_addresses=address_map
        filter_tree=config['filter_id']
        network_location=self.network_location
        lockout_time=config['lockout_time']
        funct_num=funct_num

        def setup(logging, data):
            # assign each
            data['sub_receivers'] = {
                sub_name: fsgui.network.UnidirectionalChannelReceiver(sub_address)
                for sub_name, sub_address in sub_addresses.items()
            }

            data['sub_values'] = {
                sub_name: False
                for sub_name in sub_addresses.keys()
            }

            data['trodes_sender'] = trodesnetwork.ServiceConsumer('trodes.hardware', server_address = f'{network_location.address}:{network_location.port}')

            data['last_triggered'] = None
            data['currently_triggered'] = False

        def workload(logging, messages, publisher, reporter, data):
            # loop updates all of the sub_values
            for sub_name, receiver in data['sub_receivers'].items():
                value = receiver.recv(timeout=0)
                if value is not None:
                    data['sub_values'][sub_name] = value

            def evaluate_node(node, data):
                if 'gate' == node['data']['type']:
                    if 'gate-and' == node['data']['value']:
                        return functools.reduce(operator.and_, map(lambda n: evaluate_node(n, data), node['children']))
                    elif 'gate-or' == node['data']['value']:
                        return functools.reduce(operator.or_, map(lambda n: evaluate_node(n, data), node['children']))
                    elif 'gate-nand' == node['data']['value']:
                        return not functools.reduce(operator.and_, map(lambda n: evaluate_node(n, data), node['children']))
                elif 'filter' == node['data']['type']:
                    value = data['sub_values'][node['data']['value']]
                    return value
                else:
                    raise ValueError('evaluate error: {}'.format(node))
            
            evaluation = evaluate_node(filter_tree, data)
            
            if evaluation and (data['last_triggered'] is None or time.time() > data['last_triggered'] + lockout_time / 1000.0):
                data['last_triggered'] = time.time()
                data['trodes_sender'].request([
                    'tag',
                    'HRSCTrig',
                    {'fn': funct_num}
                ])
                data['currently_triggered'] = True
                reporter.send({'val': True})
            elif not evaluation and data['currently_triggered']:
                data['trodes_sender'].request([
                    'tag',
                    'HRSCTrig',
                    {'fn': funct_num + 1}
                ])
                data['currently_triggered'] = False
                data['last_triggered'] = None
                reporter.send({'val': False})
 
        return fsgui.process.build_process_object(setup, workload)