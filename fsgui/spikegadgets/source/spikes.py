import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging


class SpikesDataType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='Trodes Spikes',
            datatype='float',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Trodes Spikes',
                'tetrodeNum': None,
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
                'label': 'Tetrode number',
                'name': 'tetrodeNum',
                'type': 'select',
                'options': [
                    {'name': f'{tet}', 'label': f'Tetrode {tet}'} for tet in [1,2,3]
                ],
                'default': config['tetrodeNum'],
                'tooltip': 'Tetrode number to receive spikes data from',
            },
        ]
