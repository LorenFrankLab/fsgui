import fsgui.simulation.bins

class SimulationNodeProvider:
    def get_nodes(self):
        return [
            fsgui.simulation.bins.BinGeneratorType('bin-generator-type')
        ]
