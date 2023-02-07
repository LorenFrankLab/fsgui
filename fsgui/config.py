import json

class FileConfig:
    def __init__(self, filename):
        self.filename = filename

        try:
            with open(self.filename, 'r') as f:
                contents = f.read()
            obj = json.loads(contents)
            self.nodes = obj['nodes']
        except FileNotFoundError as e:
            with open(self.filename, 'w') as f:
                pass
 
            self.nodes = []

        except json.JSONDecodeError as e:
            with open(self.filename, 'w') as f:
                pass
 
            self.nodes = []

    def node_configs(self):
        return self.nodes
     
    def write_config(self, nodes):
        content = json.dumps({'nodes': nodes}, indent='    ')
        with open(self.filename, 'w') as f:
            f.write(content)
