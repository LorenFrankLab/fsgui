class Tree:
    """
    A data structure that is based on ids. It can be useful when a GUI component
    is managing data.
    """

    def __init__(self, id_manager):
        self._id_manager = id_manager
        self._root = None
 
    def is_empty(self):
        return self._root is None

    def set_structure(self, root):
        self._root = root

    def add_item(self, target_id, data):
        """
        target_id: if none, we assume it's the root
        """
        new_node = {
            'id': self._id_manager.assign(),
            'data': data,
            'children': []
        }

        if target_id is None:
            self._root = new_node
        else:
            queue = [self._root]
            while len(queue) > 0:
                node = queue.pop()
                if node['id'] == target_id:
                    node['children'].append(new_node)
                    break
                else:
                    for child in node['children']:
                        queue.append(child)

    def delete_by_id(self, target_id):
        if self._root['id'] == target_id:
            self._root = None
        else:
            queue = [self._root]
            while len(queue) > 0:
                node = queue.pop()
                node['children'] = [n for n in node['children'] if n['id'] != target_id]
                for child in node['children']:
                    queue.append(child)

    def get_root(self):
        return self._root
