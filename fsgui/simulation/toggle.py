import fsgui.node
import fsgui.process
import multiprocessing as mp
import random
import time

class ToggleSourceType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='Toggle source type',
            datatype='bool',
        )
    
    def write_template(self, config = None):
        config = config if config is not None else {
            'type_id': self.type_id(),
            'instance_id': '',
            'nickname': self.name(),
            'value': False,
            'sample_rate': 1500,
        }

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
                'label': 'Filter output value',
                'name': 'value',
                'type': 'boolean',
                'default': config['value'],
                'tooltip': 'The value to send.',
                'live_editable': True,
            },
            {
                'label': 'Sample rate',
                'name': 'sample_rate',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['sample_rate'],
                'units': 'Hz',
                'tooltip': 'The rate at which to send the data.'
            },
 
        ]
    
    def build(self, config, param_map):
        def setup(connection, data):
            pass

        def workload(connection, publisher, reporter, data):
            if connection.pipe_poll(timeout = 0):
                msg_tag, msg_data = connection.pipe_recv()
                if msg_tag == 'update':
                    msg_varname, msg_value = msg_data
                    config[msg_varname] = msg_value
            
            publisher.send(config['value'])
            reporter.send({'toggle_value': config['value']})
            time.sleep(1.0/config['sample_rate'])
        
        return fsgui.process.build_process_object(setup, workload)
