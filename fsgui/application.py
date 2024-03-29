"""
"""
import itertools
import fsgui.config
import fsgui.util
import logging
import multiprocessing as mp
import multiprocessing.connection
import traceback
import copy

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
    def __init__(self, node_providers=[], config = []):
        self.uid_manager = fsgui.util.UIDManager()

        self.added_nodes = {
            node['instance_id'] : NodeObject(type_id=node['type_id'], instance_id=node['instance_id'], param_config=node)
            for node in config
        }

        self.available_types = {
            node_type.type_id() : NodeType(type_id=node_type.type_id(), node_class=node_type.node_class(), type_object=node_type)
            for node_type in itertools.chain.from_iterable([provider.get_nodes() for provider in node_providers])
        }
    
    def process_items(self):
        conn_dict = {node.built_process[0]: node for node in self.added_nodes.values() if node.built_process is not None}
        conns = list(conn_dict.keys())
        ready_conns = multiprocessing.connection.wait(conns, timeout=0)

        for conn in ready_conns:
            try:
                data = conn.recv()
                assert 'type' in data

                if data['type'] == 'exception':
                    e = data['error']
                    trace_string = data['trace_string']
                    logging.info(f'<pre>{trace_string}</pre>')
                    logging.error(f'{repr(e)}')
                elif data['type'] == 'log_debug':
                    logging.debug(data['data'])
                elif data['type'] == 'log_info':
                    logging.info(data['data'])
                elif data['type'] == 'log_warning':
                    logging.warning(data['data'])
                elif data['type'] == 'log_error':
                    logging.error(data['data'])
                elif data['type'] == 'log_critical':
                    logging.critical(data['data'])
                else:
                    raise ValueError('unknown type {}'.format(data['type']))
            except EOFError as e:
                # this is a good hint that the process has been taken down, so maybe forcibly unbuild the process?
                # and possibly set error status
                conn_dict[conn].built_process = None
                conn_dict[conn].build_error = "Process crashed."

    
    def send_message_to_process(self, node_id, message):
        if self.added_nodes[node_id].built_process is not None:
            process_pipe = self.added_nodes[node_id].built_process[0]
            process_pipe.send(message)
        else:
            raise ValueError(f"Can not send message to {node_id}. The process is not built. Tried to send: {message}")

    def get_save_config(self):
        return [node.param_config for node in self.added_nodes.values()]

    def get_reporters_map(self):
        return {
            node_id: node.built_process[2]
            for node_id, node in self.added_nodes.items()
            if node.built_process is not None
        }

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

    def create_node(self, config):
        instance_id = self.uid_manager.assign()
        config['instance_id'] = instance_id
        self.added_nodes[instance_id] = NodeObject(type_id=config['type_id'], instance_id=instance_id, param_config=config)
        return instance_id

    def duplicate_node(self, old_instance_id):
        instance_id = self.uid_manager.assign()
        config = copy.deepcopy(self.added_nodes[old_instance_id].param_config)
        config['instance_id'] = instance_id
        config['nickname'] = 'Copy of {}'.format(config['nickname'])
        self.added_nodes[instance_id] = NodeObject(type_id=config['type_id'], instance_id=instance_id, param_config=config)
        return instance_id

    def edit_node(self, config):
        instance_id = config['instance_id']
        node = self.added_nodes[instance_id]

        # edit goes straight without regard to build status
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
            if child_id is None:
                raise ValueError(f'While building "{node.nickname}": one of the children instance_ids has a value of {None}. Please make sure node is properly configured.')
            self.__build_recursive(child_id)

        node = self.added_nodes[instance_id]
        self.__build_node_if_not_built(instance_id, node.param_config)

    def __build_node_if_not_built(self, instance_id, config):
        node = self.added_nodes[instance_id]

        pipe_receiver_dict = {}

        for param_value_id in self.get_node_children_ids(instance_id):
            param_node = self.added_nodes[param_value_id]
            pipe_receiver, pipe_sender = mp.Pipe(duplex=False)
            param_node.built_process[4].send(pipe_sender)
            pipe_receiver_dict[param_value_id] = pipe_receiver

        if node.built_process is None:
            try:
                built_process = self.available_types[node.type_id].type_object.build(node.param_config, pipe_receiver_dict)
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
