class TrodesNetworkLocation:
    def __init__(self, address, port):
        self._address = address
        self._port = port

    @property
    def address(self):
        return self._address

    @property
    def port(self):
        return self._port

class TrodesSpawnArgParser:
    """
    In Trodes, when a module is being spawned, an absolute path to the executable is generated
    and a new process is spawned with these arguments, for example:
        -trodesConfig, /path/to/config.trodesconf, -serverAddress, tcp://127.0.0.1, -serverPort, 49152
    """
    def parse_args(self, argv):
        """
        Runs on inputs that you would get from calling sys.argv.
        """
        try:
            # extremely fragile, but it should change only when Trodes calls modules in a different way
            return {'trodesConfig': argv[2], 'serverAddress': argv[4], 'serverPort': int(argv[6])}
        except IndexError as err:
            raise ValueError('Received unexpected arguments format.') from err
