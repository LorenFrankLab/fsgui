import fsgui.network
import multiprocessing as mp
import logging
import traceback

def build_process_object(setup, workload, cleanup=None):
    if cleanup is None:
        def cleanup(reporter, data):
            pass

    app_conn, process_conn = mp.Pipe(duplex=True)

    process_addpub_conn, app_addpub_conn = mp.Pipe(duplex=False)

    process_object = ProcessObject(process_conn, process_addpub_conn, setup, workload, cleanup)

    pub_address = app_conn.recv()
    reporter_address = app_conn.recv()

    return app_conn, pub_address, reporter_address, process_object, app_addpub_conn

class ProcessConnection:
    def __init__(self, conn):
        self.conn = conn
    
    def __send(self, data):
        self.conn.send(data)
    
    def __send_message(self, message_type, message_data):
        self.__send({
            'type': message_type,
            'data': message_data,
        })

    def debug(self, message):
        self.__send_message('log_debug', message)
    
    def info(self, message):
        self.__send_message('log_info', message)

    def warning(self, message):
        self.__send_message('log_warning', message)

    def error(self, message):
        self.__send_message('log_error', message)

    def critical(self, message):
        self.__send_message('log_critical', message)
    
    def exception(self, e):
        self.__send({
            'type': 'exception',
            'error': e,
            'trace_string': ''.join(traceback.format_exception(type(e), e, e.__traceback__)),
        })

    def pipe_recv(self):
        return self.conn.recv()

    def pipe_poll(self, timeout):
        return self.conn.poll(timeout)
    
class MultiPublisher:
    def __init__(self, pipe_list):
        self.pipe_list = pipe_list

    def send(self, data):
        for pipe in self.pipe_list:
            try:
                pipe.send(data)
            except BrokenPipeError as e:
                self.pipe_list.remove(pipe)

class ProcessObject:
    def __init__(self, process_conn, addpub_conn, setup, workload, cleanup):
        """
        setup: acts upon process-local data, queues, conns, and may also create resources (e.g. internet conn)
        workload: executes on process-local data and may access resources (e.g. gpu), may access time
        cleanup: a function that disposes of resources and may close queues
        """
        # we don't keep a pointer to stop_recv so that garbage collection can happen when the thread finishes 
        stop_recv, self._stop_sender = mp.Pipe(duplex=False)

        self._proc = mp.Process(target=self._run, args=(process_conn, addpub_conn, setup, workload, cleanup, stop_recv,))
        self._proc.start()

    def _run(self, process_conn, addpub_conn, setup, workload, cleanup, stop_receiver):
        """
        This is the shell of the computation that abstracts away the flow control
        """
        connection = ProcessConnection(process_conn)

        publisher = fsgui.network.UnidirectionalChannelSender()
        process_conn.send(publisher.get_location())

        reporter = fsgui.network.UnidirectionalChannelSender()
        process_conn.send(reporter.get_location())

        pipes_to_publish_on = []

        real_publisher = MultiPublisher(pipes_to_publish_on)

        data = {}

        # new objects can be saved to the data dict
        try:
            setup(connection, data)
            while not stop_receiver.poll():
                if addpub_conn.poll(timeout = 0):
                    pipe = addpub_conn.recv()
                    pipes_to_publish_on.append(pipe)

                workload(connection, real_publisher, reporter, data)
        except Exception as e:
            connection.exception(e)
        finally:
            cleanup(connection, data)

    def __del__(self):
        """
        Following the semantics of RAII, we want to shut down the process when we're destroying
        the object. Joining the process at the end of cleanup can be complicated if queues are
        used by the process and are not properly cleaned up.
        """
        try:
            # with no correct way to check if the process is still
            # running, we send the end signal
            self._stop_sender.send(True)
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