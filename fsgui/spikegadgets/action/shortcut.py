import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import functools
import operator
import time



class StateScriptFunctionActionType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        name = 'StateScript function'
        super().__init__(
            type_id=type_id,
            node_class='action',
            name=name,
            datatype=None,
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'filter_id': None,
                'lockout_time': 0,
                'functNum': 0,
            }
        )

        self.network_location = network_location

    def get_gui_config(self):
        return [
            {
                'type': 'checkbox',
                'label': 'enabled',
                'checked': 'start',
                'unchecked': 'stop',
            }
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
        return fsgui.spikegadgets.action.build_shortcut_command(
            pipe_map=address_map,
            filter_tree=config['filter_id'],
            network_location=self.network_location,
            lockout_time=config['lockout_time'],
            on_funct_num=config['functNum'],
        )
