import fsgui.mock.source

class MockNodeProvider:
    def get_nodes(self):
        return [
            fsgui.mock.source.BinGeneratorType('bin-generator-type'),
        ]
