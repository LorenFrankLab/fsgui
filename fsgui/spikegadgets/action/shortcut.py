import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodesnetwork as trodesnetwork

import time



class StateScriptFunctionActionType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        super().__init__(
            type_id=type_id,
            node_class='action',
            name='StateScript Function',
            datatype=None,
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Digital Pulsetrain',
                'filter_id': None,
                'lockout_time': 0,
                'functNum': 0,
            }
        )

        self.network_location = network_location

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
            {
                'label': 'Lockout time',
                'name': 'lockout_time',
                'type': 'integer',
                'lower': 0,
                'upper': 100000,
                'default': config['lockout_time'],
                'tooltip': 'Time in milliseconds to wait before triggering again.',
            },
            {
                'label': 'Function number',
                'name': 'functNum',
                'type': 'integer',
                'lower': 0,
                'upper': 32,
                'default': config['functNum'],
                'tooltip': 'StateScript function number to run.',
            },
        ]

    def build(self, config, address_map):
        return StateScriptFunctionActionProcess(
            sub_addresses=address_map,
            filter_tree=config['filter_id'],
            network_location=self.network_location,
            lockout_time=config['lockout_time'],
            funct_num=config['functNum']
        )

class StateScriptFunctionActionProcess:
    def __init__(self, sub_addresses, filter_tree, network_location, lockout_time, funct_num):
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

            data['trodes_sender'] = trodesnetwork.ServiceConsumer('trodes.hardware', server_address = f'{network_location.address}:{network_location.port}')

            data['last_triggered'] = None

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
            
            if evaluation and (data['last_triggered'] is None or time.time() > data['last_triggered'] + lockout_time / 1000.0):
                data['last_triggered'] = time.time()
                data['trodes_sender'].request([
                    'tag',
                    'HRSCTrig',
                    {'fn': funct_num}
                ])

        def cleanup(data):
            pass

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()
 