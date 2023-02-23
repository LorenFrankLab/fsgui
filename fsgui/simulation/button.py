import fsgui.node
import fsgui.process
import multiprocessing as mp
import random
import time

class ButtonSourceType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name='Button source type'
        super().__init__(
            type_id=type_id,
            node_class='source',
            name=name,
            datatype='bool',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
            }
        )
    
    def get_gui_config(self):
        return [
            {
                'type': 'button',
                'label': 'Turn on',
                'pressed': True,
                'released': False,
            },
        ]

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
        def setup(connection, data):
            data['value'] = False

        def workload(connection, publisher, reporter, data):
            if connection.pipe_poll(timeout = 0):
                msg_data = connection.pipe_recv()
                data['value'] = msg_data
                print(f'received: {msg_data}')

            publisher.send(data['value'])
            reporter.send({'button_value': data['value']})
            time.sleep(0.000666)
        
        return fsgui.process.build_process_object(setup, workload)
