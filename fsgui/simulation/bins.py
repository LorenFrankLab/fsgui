import fsgui.node
import fsgui.process
import multiprocessing as mp
import random
import time
import numpy as np

class BinGeneratorType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name='Bin generator type'
        super().__init__(
            type_id=type_id,
            node_class='source',
            name=name,
            datatype='bin_id',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
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
        ]
    
    def build(self, config, param_map):
        smoothing = 0.1
        dt = 0.01

        def setup(logging, data):
            data['y_cumulative'] = 0
            data['y_smoothed'] = 0

        def workload(connection, publisher, reporter, data):
            # some sort of brownian motion
            x = np.random.normal(0, 1) * np.sqrt(dt) + 0.01
            data['y_cumulative'] += x
            data['y_smoothed'] = (1 - smoothing) * data['y_smoothed'] + smoothing * data['y_cumulative']

            value = int(data['y_smoothed']) % 20

            publisher.send(value)
            reporter.send({'bin_value': value})
            time.sleep(0.01)
        
        return fsgui.process.build_process_object(setup, workload)
