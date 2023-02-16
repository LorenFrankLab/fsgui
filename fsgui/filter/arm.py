import fsgui.node

class ArmFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name='Arm filter type'
        super().__init__(
            type_id=type_id,
            node_class='filter',
            name=name,
            datatype='discrete_distribution',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'posterior_source': None,
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
                'label': 'Posterior source',
                'name': 'posterior_source',
                'type': 'node:discrete_distribution',
                'default': config['posterior_source'],
                'tooltip': 'This node a distribution of a posterior to be summed.',
            },
        ]
