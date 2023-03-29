class NodeTypeObject:
    def __init__(self, type_id, node_class, name, datatype, default = None):
        self._type_id = type_id
        self._node_class = node_class
        self._name = name
        self._datatype = datatype
        self._default = default
    
    def type_id(self):
        return self._type_id

    def node_class(self):
        return self._node_class

    def name(self):
        return self._name
    
    def datatype(self):
        return self._datatype

    def default(self):
        return self._default