import multiprocessing as mp
import functools
import logging
import fsgui.reporter

def build_process_object(setup, workload, cleanup):
    app_conn, process_conn = mp.Pipe(duplex=True)
    process_object = ProcessObject(process_conn, setup, workload, cleanup)
    pub_address = app_conn.recv()
    return app_conn, pub_address, process_object

class ProcessObject:
    def __init__(self, process_conn, setup, workload, cleanup):
        """
        setup: acts upon process-local data, queues, conns, and may also create resources (e.g. internet conn)
        workload: executes on process-local data and may access resources (e.g. gpu), may access time
        cleanup: a function that disposes of resources and may close queues
        """
        # we don't keep a pointer to ctrl_recv so that garbage collection can happen when the thread finishes 
        self._last_signal_sent = None
        ctrl_recv, self._ctrl_sender = mp.Pipe(duplex=False)

        self._proc = mp.Process(target=self._run, args=(process_conn, setup, workload, cleanup, ctrl_recv,))
        self._proc.start()

        self.start()

    def _run(self, process_conn, setup, workload, cleanup, ctrl_receiver):
        """
        This is the shell of the computation that abstracts away the flow control of starting and pausing computation.
        """
        reporter = fsgui.reporter.ProcessReporter(process_conn)

        publisher = fsgui.network.UnidirectionalChannelSender()
        reporter._send_pub_location(publisher.get_location())

        data = {}

        # new objects can be saved to the data dict
        try:
            setup(reporter, data)
        except Exception as e:
            reporter.exception(e)
            cleanup(reporter, data)
            return

        # waiting for a signal {start, end} and blocking infinitely long
        while ctrl_receiver.poll(timeout=None):
            # we should be the sole owner of ctrl_receiver, so no we should receive immediately here
            signal = ctrl_receiver.recv()
            if signal == 'start':
                # we proceed to enter the loop
                pass
            elif signal == 'end':
                # we skip to the cleanup code
                break
            else:
                raise AssertionError('Unknown control signal (should be "start" or "end")')

            # as long as there's no signal {pause, end}, we jump into the loop w/o blocking
            while not ctrl_receiver.poll():
                try:
                    workload(reporter, publisher, data)
                except Exception as e:
                    reporter.exception(e)
                    cleanup(reporter, data)
                    return

            # we should receive immediately here
            signal = ctrl_receiver.recv()
            if signal == 'pause':
                # we go to the top to wait for a start signal
                pass
            elif signal == 'end':
                break
            else:
                raise AssertionError('Unknown control signal (should be "pause" or "end")')
        try:
            cleanup(reporter, data)
        except Exception as e:
            reporter.exception(e)
            return

    def start(self):
        if self._last_signal_sent == 'start':
            raise ValueError('already started')

        try:
            # if the thing hasn't been ended
            self._ctrl_sender.send('start')
        except BrokenPipeError as e:
            # clearly the process is gone
            assert not self._proc.is_alive()
            raise ValueError('process died')

        self._last_signal_sent = 'start'

    def pause(self):
        if self._last_signal_sent is None or self._last_signal_sent == 'pause':
            raise ValueError('already paused')

        try:
            # if the thing hasn't been ended
            self._ctrl_sender.send('pause')
        except BrokenPipeError as e:
            # clearly the process is gone
            assert not self._proc.is_alive()
            raise ValueError('process died')

        self._last_signal_sent = 'pause'

    def __del__(self):
        """
        Following the semantics of RAII, we want to shut down the process when we're destroying
        the object. Joining the process at the end of cleanup can be complicated if queues are
        used by the process and are not properly cleaned up.
        """
        try:
            # with no correct way to check if the process is still
            # running, we send the end signal
            self._ctrl_sender.send('end')
        except BrokenPipeError:
            # if the process is not running at the time the signal is sent
            # then we silently ignore the error because the process is already ended
            pass
        finally:
            # we verify that the process is not running anymore
            # this can be complicated by improper queue cleanup
            self._proc.join()
            assert not self._proc.is_alive()
            logging.info(f'Deconstructor called: {self}')