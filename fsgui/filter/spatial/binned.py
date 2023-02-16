import fsgui.node

class LinearBinningFilterType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id):
        name = 'Linear binning filter'

        super().__init__(
            type_id=type_id,
            node_class='filter',
            name=name,
            datatype='bin_id',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'spatial_source_id': None,
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
                'label': 'Spatial source',
                'name': 'spatial_source_id',
                'type': 'node:point2d',
                'default': config['spatial_source_id'],
                'tooltip': 'Source of point2d spatial data (e.g. camera)',
            },
       ]