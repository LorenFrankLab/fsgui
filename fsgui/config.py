import json
import oyaml as yaml

class FileConfig:
    def __init__(self, filename):
        self.filename = filename

        try:
            with open(self.filename, 'r') as f:
                contents = f.read()
            obj = yaml.load(contents, Loader=yaml.FullLoader)
            self.nodes = obj['nodes']
        
        except FileNotFoundError as e:
            self.nodes = []

    def node_configs(self):
        return self.nodes
     
    def write_config(self, nodes):
        with open(self.filename, 'w') as f:
            f.write(yaml.dump({'nodes': nodes}))
