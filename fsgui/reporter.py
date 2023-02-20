import threading
import traceback
import multiprocessing as mp
import logging
import queue

class ProcessReporter:
    def __init__(self, conn):
        self.conn = conn
    
    def __send(self, data):
        self.conn.send(data)
    
    def __send_message(self, message_type, message_string):
        self.__send({
            'type': message_type,
            'string': message_string,
        })

    def debug(self, message):
        self.__send_message('debug_message', message)
    
    def info(self, message):
        self.__send_message('info_message', message)

    def warning(self, message):
        self.__send_message('warning_message', message)

    def error(self, message):
        self.__send_message('error_message', message)

    def critical(self, message):
        self.__send_message('critical_message', message)
    
    def exception(self, exception):
        self.__send({
            'type': 'exception',
            'exception': exception,
        })
    
    def add_endpoint(self, endpoint):
        self.__send({
            'type': 'add_endpoint',
            'endpoint': endpoint
        })

    def _send_pub_location(self, location):
        self.__send(location)
