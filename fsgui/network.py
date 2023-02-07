import zmq

class UnidirectionalChannelSender:
    def __init__(self, location=None):
        self._ctx = zmq.Context()
        self._sock = self._ctx.socket(zmq.PUB)

        if location is not None:
            self._sock.bind(location)
            self._location = location
        else:
            self._sock.bind_to_random_port('tcp://0.0.0.0')
            self._location = self._sock.get_string(zmq.LAST_ENDPOINT)

    def send(self, data):
        self._sock.send_string(data)

    def get_location(self):
        return self._location

class UnidirectionalChannelReceiver:
    def __init__(self, location):
        self._ctx = zmq.Context()
        self._sock = self._ctx.socket(zmq.SUB)
        self._sock.connect(location)
        self._sock.setsockopt_string(zmq.SUBSCRIBE, '')

        self._poller = zmq.Poller()
        self._poller.register(self._sock)

    def recv(self, timeout=None):
        polled = self._poller.poll(timeout)
        if len(polled) > 0:
            (sock, mask), = polled
            # not sure about mask
            assert mask == 1
            return sock.recv_string()
        else:
            return None