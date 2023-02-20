"""
"""
import itertools
import fsgui.config
import fsgui.util
import logging
import multiprocessing as mp
import multiprocessing.connection
import traceback

class NodeObject:
    def __init__(self, type_id, instance_id, param_config):
        self.type_id = type_id
        self.instance_id = instance_id
        self.param_config = param_config
        # this object can be started/stopped
        self.built_process = None
        self.build_error = None

    @property
    def nickname(self):
        return self.param_config['nickname']

    @property
    def status(self):
        assert self.built_process is None or self.build_error is None

        if self.build_error is not None:
            return 'error'
        else:
            return 'built' if self.built_process is not None else 'unbuilt'

class NodeType:
    def __init__(self, type_id, node_class, type_object):
        self.type_id = type_id
        self.node_class = node_class
        self.type_object = type_object

    @property
    def name(self):
        return self.type_object.name()
    
    @property
    def datatype(self):
        return None
    
class FSGuiApplication:
    def __init__(self, node_providers=[], config=None):
        if config is None:
            config = fsgui.config.EmptyConfig()
        self.config = config

        self.uid_manager = fsgui.util.UIDManager()

        self.added_nodes = {
            node['instance_id'] : NodeObject(type_id=node['type_id'], instance_id=node['instance_id'], param_config=node)
            for node in config.node_configs()
        }

        self.available_types = {
            node_type.type_id() : NodeType(type_id=node_type.type_id(), node_class=node_type.node_class(), type_object=node_type)
            for node_type in itertools.chain.from_iterable([provider.get_nodes() for provider in node_providers])
        }
    
    def process_items(self):
        conns = [node.built_process[0] for node in self.added_nodes.values() if node.built_process is not None]
        ready_conns = multiprocessing.connection.wait(conns, timeout=0)

        for conn in ready_conns:
            data = conn.recv()
            assert 'type' in data

            if data['type'] == 'exception':
                e = data['exception']
                trace_string = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                logging.info(f'<pre>{trace_string}</pre>')
                logging.exception(f'{repr(e)}')
            elif data['type'] == 'debug_message':
                logging.debug(data['string'])
            elif data['type'] == 'info_message':
                logging.info(data['string'])
            elif data['type'] == 'warning_message':
                logging.warning(data['string'])
            elif data['type'] == 'error_message':
                logging.error(data['string'])
            elif data['type'] == 'critical_message':
                logging.critical(data['string'])
            elif data['type'] == 'add_endpoint':
                self.add_node_reporting_endpoint(data['endpoint'])
            else:
                raise ValueError('unknown type {}'.format(data['type']))

    def add_node_reporting_endpoint(self, endpoint):
        print(f'got an endpoint: {endpoint}')
    
    def build_all(self):
        for instance_id in self.added_nodes.keys():
            try:
                self.__build_recursive(instance_id)
            except Exception as e:
                pass

    def get_nodes_datatype(self, datatype):
        return [node for node in self.added_nodes.values() if self.available_types[node.type_id].type_object.datatype() == datatype]

    def get_configs(self):
        def get_node_tuple(node):
            return (
                node.nickname,
                node.instance_id,
                node.status,
                self.available_types[node.type_id].type_object.write_template(node.param_config)
            )
        
        def get_type_tuple(node_type):
            return (
                node_type.type_id,
                node_type.name,
                node_type.type_object.write_template()
            )

        return {
            'source_nodes': [
                get_node_tuple(node)
                for node in self.added_nodes.values() if self.available_types[node.type_id].node_class == 'source'],
            'filter_nodes': [
                get_node_tuple(node)
                for node in self.added_nodes.values() if self.available_types[node.type_id].node_class == 'filter'],
            'action_nodes': [
                get_node_tuple(node)
                for node in self.added_nodes.values() if self.available_types[node.type_id].node_class == 'action'],
            'source_types': [
                get_type_tuple(node_type)
                for node_type in self.available_types.values() if node_type.node_class == 'source'],
            'filter_types': [
                get_type_tuple(node_type)
                for node_type in self.available_types.values() if node_type.node_class == 'filter'],
            'action_types': [
                get_type_tuple(node_type)
                for node_type in self.available_types.values() if node_type.node_class == 'action'],
        }
    
    def __get_nodes_datatype(self, datatype):
        return [ node for node in self.added_nodes.values() if self.available_types[node.type_id].datatype == datatype]

    def __del__(self):
        logging.info(f'Deleting: {self}')
        self.__write_configuration()

    def __write_configuration(self):
        self.config.write_config([node.param_config for node in self.added_nodes.values()])
        logging.info(f'Saved: {self.config}')

    def create_node(self, config):
        instance_id = self.uid_manager.assign()
        config['instance_id'] = instance_id
        self.added_nodes[instance_id] = NodeObject(type_id=config['type_id'], instance_id=instance_id, param_config=config)
        return instance_id

    def edit_node(self, config):
        instance_id = config['instance_id']
        node = self.added_nodes[instance_id]
        if node.built_process is not None:
            raise ValueError('The node is currently built. Can not edit a built node. Please unbuild.')
        node.param_config = config

        return instance_id

    def build_node(self, instance_id):
        node = self.added_nodes[instance_id]

        if node.built_process is not None:
            raise ValueError('The node is already built. Can not build an already-built node.')

        self.__build_recursive(instance_id)
    
    def __build_recursive(self, instance_id):
        node = self.added_nodes[instance_id]
        typedict = self.__get_param_type_dict(instance_id)
        params = node.param_config

        children_ids = self.get_node_children_ids(instance_id)

        for child_id in children_ids:
            self.__build_recursive(child_id)

        addr_map = self.__get_child_address_map(instance_id)

        node = self.added_nodes[instance_id]
        self.__build_node_if_not_built(instance_id, node.param_config, addr_map)

    def __build_node_if_not_built(self, instance_id, config, addr_map):
        node = self.added_nodes[instance_id]
        if node.built_process is None:
            try:
                built_process = self.available_types[node.type_id].type_object.build(node.param_config, addr_map)
                assert built_process is not None
                node.build_error = None
                node.built_process = built_process
            except BaseException as e:
                node.build_error = repr(e)
                node.built_process = None
                raise e

    def get_node_children_ids(self, instance_id):
        node = self.added_nodes[instance_id]
        type_dict = self.__get_param_type_dict(instance_id)

        def get_instance_ids(param_value, vartype):
            if vartype == 'node:tree':
                if param_value is None:
                    return []

                list_ids = []
                bfs_queue = [param_value]

                while len(bfs_queue) > 0:
                    current_node = bfs_queue.pop()

                    if current_node['data']['type'] == 'filter':
                        list_ids.append(current_node['data']['value'])

                    for child in current_node['children']:
                        bfs_queue.append(child)
                
                return list_ids
            if vartype in ['node:float', 'node:bool', 'node:point2d', 'node:bin_id', 'node:spikes', 'node:bin_id', 'node:discrete_distribution', 'node:timestamp']:
                return [param_value]
            else:
                logging.warning(f'vartype not explicitly listed to be handled: {vartype}')
                return [param_value]

        return list(itertools.chain.from_iterable([
            get_instance_ids(node.param_config[varname], vartype)
            for varname, vartype in type_dict.items() 
            if vartype.startswith('node:')]))

    def __get_child_address_map(self, instance_id):
        return {
            instance_id : self.added_nodes[instance_id].built_process[1]
            for instance_id in self.get_node_children_ids(instance_id)
        }

    def __get_param_type_dict(self, instance_id):
        return {
            item['name']: item['type']
            for item in self.available_types[self.added_nodes[instance_id].type_id].type_object.write_template()
        }

    def unbuild_node(self, instance_id):
        node = self.added_nodes[instance_id]

        if node.built_process is None:
            raise ValueError('The node is not built. Can not unbuild a node that is not built.')

        for node_id, n in self.added_nodes.items():
            if instance_id in self.get_node_children_ids(node_id):
                if self.added_nodes[node_id].status == 'built':
                    raise ValueError(f'Node: "{self.added_nodes[node_id].nickname}" depends on this node. Unbuild that one first.')

        built_process = node.built_process
        del built_process
        node.built_process = None

    def __unbuild_recursive(self, instance_id):
        pass

    def delete_node(self, instance_id):
        node = self.added_nodes[instance_id]

        if node.built_process is not None:
            raise ValueError('The node built. Can not delete a node that is built.')
        else:
            self.__unbuild_recursive(instance_id)

        node = self.added_nodes.pop(instance_id)
        del node
