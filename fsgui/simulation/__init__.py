import fsgui.simulation.bins
import fsgui.simulation.button

class SimulationNodeProvider:
    def get_nodes(self):
        return [
            fsgui.simulation.bins.BinGeneratorType('bin-generator-type'),
            fsgui.simulation.button.ButtonSourceType('button-source-type'),
        ]
