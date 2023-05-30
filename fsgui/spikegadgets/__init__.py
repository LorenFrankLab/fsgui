import fsgui.spikegadgets.source.camera
import fsgui.spikegadgets.source.binned_camera
import fsgui.spikegadgets.source.lfp
import fsgui.spikegadgets.source.spikes
import fsgui.spikegadgets.source.timestamp
import fsgui.spikegadgets.action.pulse
import fsgui.spikegadgets.action.shortcut

class SpikeGadgetsNodeProvider:
    def __init__(self, network_location):
        self.network_location = network_location

    def get_nodes(self):
        return [
            # sources
            fsgui.spikegadgets.source.camera.CameraDataType('trodes-camera-data-type', self.network_location),
            fsgui.spikegadgets.source.binned_camera.LinearizedBinnedCameraType('trodes-linearized-binned-camera-type', self.network_location),
            fsgui.spikegadgets.source.lfp.LFPDataType('trodes-lfp-data-type', self.network_location),
            fsgui.spikegadgets.source.spikes.SpikesDataType('trodes-spike-data-type', self.network_location),
            fsgui.spikegadgets.source.timestamp.TimestampDataType('trodes-timestamp-data-type', self.network_location),
            # actions
            fsgui.spikegadgets.action.pulse.DigitalPulseWaveActionType('trodes-digital-pulse-action-type', self.network_location),
            fsgui.spikegadgets.action.shortcut.StateScriptFunctionActionType('trodes-statescript-function-action-type', self.network_location),
        ]
