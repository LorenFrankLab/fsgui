import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodesnetwork as trodesnetwork

import time

class SpikeGadgetsActionProvider:
    def __init__(self, network_location):
        self.network_location = network_location

    def get_nodes(self):
        return [
            DigitalPulseWaveActionType('trodes-digital-pulse-action-type', self.network_location),
            StateScriptFunctionActionType('trodes-statescript-function-action-type', self.network_location),
        ]


