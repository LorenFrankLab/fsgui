import fsgui.process
import fsgui.network
import functools
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import operator
import time

def generate_statescript(function_num, pre_delay,
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

def build_shortcut_command(sub_addresses, filter_tree, network_location, lockout_time, on_funct_num, off_funct_num=None):
    def setup(reporter, data):
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
        data['enabled'] = False

    def workload(connection, publisher, reporter, data):
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
        

        evaluation = evaluate_node(filter_tree, data) if filter_tree is not None else False

        if connection.pipe_poll(timeout = 0):
            message_data = connection.pipe_recv()
            if message_data == 'start':
                data['enabled'] = True
            elif message_data == 'stop':
                data['enabled'] = False
            else:
                raise ValueError(f'message unexpected: {message_data}')
        
        evaluation = evaluation and data['enabled']
        
        if evaluation and (data['last_triggered'] is None or time.time() > data['last_triggered'] + lockout_time / 1000.0):
            data['last_triggered'] = time.time()
            data['trodes_sender'].request([
                'tag',
                'HRSCTrig',
                {'fn': on_funct_num}
            ])
            data['currently_triggered'] = True
            reporter.send({'val': True})
        elif not evaluation and data['currently_triggered']:
            if off_funct_num is not None:
                data['trodes_sender'].request([
                    'tag',
                    'HRSCTrig',
                    {'fn': off_funct_num}
                ])
            data['currently_triggered'] = False
            data['last_triggered'] = None
            reporter.send({'val': False})

    return fsgui.process.build_process_object(setup, workload)