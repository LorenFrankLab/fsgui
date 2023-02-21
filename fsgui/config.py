import json
import oyaml as yaml

class FileConfig:
    def __init__(self, filename):
        self.filename = filename
    
    def get_config(self):
        try:
            with open(self.filename, 'r') as f:
                contents = f.read()
            obj = yaml.load(contents, Loader=yaml.FullLoader)
            return obj['nodes']
        
        except FileNotFoundError as e:
            return []
     
    def write_config(self, nodes):
        with open(self.filename, 'w') as f:
            f.write(yaml.dump({'nodes': nodes}))
