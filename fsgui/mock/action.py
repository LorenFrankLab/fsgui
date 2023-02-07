import multiprocessing as mp
import fsgui.process
import fsgui.node
import time
import functools
import operator

class MockActionProvider:
    def get_nodes(self):
        return [
            PrintActionType('print-action-type'),
        ]

class PrintActionType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        super().__init__(
            type_id=type_id,
            node_class='action',
            name='Print Action',
            datatype=None,
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Print action',
                'filter_id': None,
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
                'label': 'Filter',
                'name': 'filter_id',
                'type': 'node:tree',
                'default': config['filter_id'],
                'tooltip': 'Filter on which to trigger our action',
            },
        ]

    def build(self, config, address_map):
        return PrintActionProcess(config['nickname'], address_map, config['filter_id'])

class PrintActionProcess:
    def __init__(self, nickname, sub_addresses, filter_tree):
        def setup(data):
            # assign each
            data['sub_receivers'] = {
                sub_name: fsgui.network.UnidirectionalChannelReceiver(sub_address)
                for sub_name, sub_address in sub_addresses.items()
            }

            data['sub_values'] = {
                sub_name: False
                for sub_name in sub_addresses.keys()
            }

        def workload(data):
            # loop updates all of the sub_values
            for sub_name, receiver in data['sub_receivers'].items():
                value = receiver.recv(timeout=200)
                if value is not None:
                    data['sub_values'][sub_name] = (value == 'True')

            def evaluate_node(node, data):
                if 'gate-and' == node['data']['type']:
                    return functools.reduce(operator.and_, map(lambda n: evaluate_node(n, data), node['children']))
                elif 'gate-or' == node['data']['type']:
                    return functools.reduce(operator.or_, map(lambda n: evaluate_node(n, data), node['children']))
                elif 'gate-nand' == node['data']['type']:
                    return not functools.reduce(operator.and_, map(lambda n: evaluate_node(n, data), node['children']))
                elif 'filter' == node['data']['type']:
                    value = data['sub_values'][node['data']['value']]
                    return value
                else:
                    raise ValueError
            
            evaluation = evaluate_node(filter_tree, data)
            
            import logging
            logging.info(f'{nickname}: {evaluation} ({time.ctime()})')

        def cleanup(data):
            pass

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()
    