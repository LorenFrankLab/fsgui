from fsgui.spikegadgets.source.camera import *
from fsgui.spikegadgets.source.lfp import *
from fsgui.spikegadgets.source.spikes import *
import fsgui.spikegadgets.source.timestamp
from fsgui.spikegadgets.action.pulse import *
from fsgui.spikegadgets.action.shortcut import *

class SpikeGadgetsNodeProvider:
    def __init__(self, network_location):
        self.network_location = network_location

    def get_nodes(self):
        return [
            # sources
            CameraDataType('trodes-camera-data-type', self.network_location),
            LFPDataType('trodes-lfp-data-type', self.network_location),
            SpikesDataType('trodes-spike-data-type', self.network_location),
            fsgui.spikegadgets.source.timestamp.TimestampDataType('trodes-timestamp-data-type', self.network_location),
            # actions
            DigitalPulseWaveActionType('trodes-digital-pulse-action-type', self.network_location),
            StateScriptFunctionActionType('trodes-statescript-function-action-type', self.network_location),
        ]
