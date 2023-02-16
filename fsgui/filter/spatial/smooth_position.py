import fsgui.array
import fsgui.node

class SmoothPositionFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name = 'Smooth position filter'
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name=name,
            datatype='point2d',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'source_id': None,
            }
        )

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
                'label': 'Source',
                'name': 'source_id',
                'type': 'node:point2d',
                'default': config['source_id'],
                'tooltip': 'Source to receive spatial data from',
            },
        ]

    def build(self, config, addr_map):
        source_id = config['source_id']
        pub_address = addr_map[source_id]
        return SpeedFilterProcess(pub_address)

class SmoothPositionFilterProcess:
    def __init__(self, source_pub_address):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        def setup(data):
            data['sub'] = fsgui.network.UnidirectionalChannelReceiver(source_pub_address)
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())
            data['filter_model'] = SmoothPositionFilter(coefficients=SpatialCoefficients4())

        def workload(data):
            item = data['sub'].recv(timeout=500)
            if item is not None:
                x, y = tuple(map(float, item.split(',')))
                smooth_x, smooth_y = data['filter_model'].smooth_position(x, y)
                data['publisher'].send(f'{smooth_x},{smooth_y}')

        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()
        self.pub_address = pipe_recv.recv()

class SpatialCoefficients4:
    def __init__(self):
        self.length = 4
        self.weights = np.array([
            0.31, 0.29, 0.25, 0.15
        ])

class SmoothPositionFilter:
    """
    Takes point2d and returns smoothed point2d.
    """

    def __init__(self, coefficients):
        self.coefficients = coefficients

        self.x_pos = fsgui.array.CircularArray(self.coefficients.length, dtype='float')
        self.y_pos = fsgui.array.CircularArray(self.coefficients.length, dtype='float')
        pass

    def smooth_position(self, x, y):
        self.x_pos.place(x)
        self.y_pos.place(y)

        smooth_x = np.dot(self.x_pos.get_slice(), self.coefficients.weights)
        smooth_y = np.dot(self.y_pos.get_slice(), self.coefficients.weights)

        return smooth_x, smooth_y
       