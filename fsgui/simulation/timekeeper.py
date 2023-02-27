import fsgui.node
import fsgui.process
import multiprocessing as mp
import random
import time
import numpy as np

class TimekeeperType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name='Timekeeper type'
        super().__init__(
            type_id=type_id,
            node_class='source',
            name=name,
            datatype='timestamp',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'sample_rate': 1500,
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
                'label': 'Sample rate',
                'name': 'sample_rate',
                'type': 'integer',
                'default': config['sample_rate'],
                'lower': 1,
                'upper': 30000,
            }
        ]
    
    def build(self, config, param_map):
        sample_rate = float(config['sample_rate'])

        def setup(logging, data):
            data['start_time'] = time.time()

        def workload(connection, publisher, reporter, data):
            elapsed_time = time.time() - data['start_time']
            simulated_hardware_timestamp = int(elapsed_time * 30000)

            publisher.send(simulated_hardware_timestamp)

            time.sleep(1.0/sample_rate)
        
        return fsgui.process.build_process_object(setup, workload)
