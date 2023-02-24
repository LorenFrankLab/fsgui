import fsgui.simulation.bins
import fsgui.simulation.button
import fsgui.simulation.spikes
import fsgui.simulation.toggle

class SimulationNodeProvider:
    def get_nodes(self):
        return [
            fsgui.simulation.bins.BinGeneratorType('bin-generator-type'),
            fsgui.simulation.button.ButtonSourceType('button-source-type'),
            fsgui.simulation.toggle.ToggleSourceType('toggle-source-type'),
            fsgui.simulation.spikes.SpikesGeneratorType('spikes-generator-type'),
        ]
