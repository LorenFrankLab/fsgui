import fsgui.process
import fsgui.network
import functools
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import operator
import time

def generate_statescript(function_num, pre_delay,
                            n_pulses, n_trains,
                            train_interval, sequence_period, primary_stim_pin, pulse_length, delay_flag):
    """
    The delayed stim function num is the function_num + 10
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

    #script += s2 + f'portout[25]=1' + endl
    #script += s2 + f'portout[25]=0' + endl
    if delay_flag:
        script += f'int r' + endl
        script += f'function {function_num + 10}' + endl
        script += f'r = random(200) + 300' + endl
        script += s2 + f'if ({lockout_var} == 0) do in r' + endl
    else:
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
        if n_trains == 1: # No extra scheduling
            pass
        elif n_trains != 0:
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
    if n_trains != 1:
    #if n_pulses != 0:
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
    #script += s2 + f'portout[26]=1' + endl
    #script += s2 + f'portout[26]=0' + endl
    script += s2 + f'{go_var} = 0' + endl
    script += s2 + f'portout[{primary_stim_pin}]=0' + endl
    script += 'end;' + endl

    return script

def build_shortcut_command(
        pipe_map,
        filter_tree,
        network_location,
        lockout_time,
        on_funct_num,
        action_enabled,
        off_when_false,
        delay_flag,
        condition_tree=None,
        off_funct_num=None,
    ):

    def setup(reporter, data):
        # setup each value
        data['sub_values'] = {
            sub_name: False
            for sub_name in pipe_map.keys()
        }

        data['trodes_sender'] = trodesnetwork.ServiceConsumer('trodes.hardware', server_address = f'{network_location.address}:{network_location.port}')

        # live updated variables
        data['action_enabled'] = action_enabled
        data['off_when_false'] = off_when_false
        data['delay_flag'] = delay_flag

        # runtime variables
        data['last_triggered'] = 0
        data['currently_triggered'] = False

        if data['off_when_false']:
            assert off_funct_num is not None

    def workload(connection, publisher, reporter, data):
        triggered = 0

        # update live variables
        if connection.pipe_poll(timeout = 0):
            msg_tag, msg_data = connection.pipe_recv()
            if msg_tag == 'update':
                msg_varname, msg_value = msg_data
                # update the variable
                data[msg_varname] = msg_value

                if data['off_when_false']:
                    assert off_funct_num is not None

            '''
            # for reporter/visualization
            testT = time.time()
            if (testT % 0.01 <= 1e-3): #update rate is 100Hz, will plot 1000 samples in each hit
                if triggered == 1:
                    reporter.send({
                        'OUTPUT_trigger': 1,
                        'OUTPUT_timestamp': data['last_triggered']
                        })
                else:
                    reporter.send({
                        'OUTPUT_trigger': 0,
                        'OUTPUT_timestamp': time.time()
                        })
            '''

 
        # loop updates all of the sub_values from pipe
        for sub_name, source_pipe in pipe_map.items():
            if source_pipe.poll(timeout=0):
                value = source_pipe.recv()
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

        # by default the condition is True
        condition = evaluate_node(condition_tree, data) if condition_tree is not None else True

        evaluation = evaluation and condition

        if delay_flag:
            on_funct_num_effective = on_funct_num + 10
        else:
            on_funct_num_effective = on_funct_num

        
        if data['action_enabled']:
            if evaluation:
                currentTime = time.time()
                if currentTime > data['last_triggered'] + lockout_time / 1000.0:
                    # we passed lockout time
                        
                        data['trodes_sender'].request([
                            'tag',
                            'HRSCTrig',
                            {'fn': on_funct_num_effective}
                        ])
                        print('trigger time')
                        data['last_triggered'] = time.time()
                        print(time.time())

                        triggered = 1
                        reporter.send({
                            'OUTPUT_trigger': 1,
                            'OUTPUT_timestamp': data['last_triggered']
                        })
                else:
                    pass
            else:
                if triggered == 1: #if condition is suddenly not true, sent suppress
                    if off_funct_num is not None:
                        data['trodes_sender'].request([
                                'tag',
                                'HRSCTrig',
                                 {'fn': off_funct_num}]) ###########################################################
                else:
                    currentTime = time.time()
                triggered = 0
        elif not data['action_enabled']:
            if triggered == 1:
                currentTime = time.time()
                if off_funct_num is not None:
                    data['trodes_sender'].request([
                            'tag',
                            'HRSCTrig',
                            {'fn': off_funct_num} ########################################################### 
                    ])
                triggered = 0              

                

        '''
        if data['action_enabled']:
            if evaluation:
                if data['currently_triggered']:
                    if time.time() > data['last_triggered'] + lockout_time / 1000.0:
                        # we passed lockout time
                        data['trodes_sender'].request([
                            'tag',
                            'HRSCTrig',
                            {'fn': on_funct_num}
                        ])
                        data['last_triggered'] = time.time()
                        data['currently_triggered'] = True
                    else:
                        # we're in lockout, so we must wait
                        pass
                elif not data['currently_triggered']:
                    # we passed lockout time
                    data['trodes_sender'].request([
                        'tag',
                        'HRSCTrig',
                        {'fn': on_funct_num}
                    ])
                    data['last_triggered'] = time.time()
                    data['currently_triggered'] = True
            elif not evaluation:
                if data['currently_triggered']:
                    if time.time() > data['last_triggered'] + lockout_time / 1000.0:
                        # action already ended, no need to shut off
                        data['currently_triggered'] = False
                        data['last_triggered'] = None

                    if not condition or data['off_when_false'] and off_funct_num is not None:
                        data['trodes_sender'].request([
                            'tag',
                            'HRSCTrig',
                            {'fn': off_funct_num}
                        ])
                        data['currently_triggered'] = False
                        data['last_triggered'] = None

        elif not data['action_enabled']:
            # we're disabled, so we want to check
            if data['currently_triggered']:
                if time.time() > data['last_triggered'] + lockout_time / 1000.0:
                    # action already ended, no need to shut off
                    data['currently_triggered'] = False
                    data['last_triggered'] = None
                else:
                    # we shut off when the action is disabled
                    if off_funct_num is not None:
                        data['trodes_sender'].request([
                            'tag',
                            'HRSCTrig',
                            {'fn': off_funct_num}
                        ])
                    data['currently_triggered'] = False
                    data['last_triggered'] = None
        '''

    return fsgui.process.build_process_object(setup, workload)