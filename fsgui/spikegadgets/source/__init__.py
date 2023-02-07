import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging

class SpikeGadgetsSourceProvider:
    def __init__(self, network_location):
        self.network_location = network_location

    def get_nodes(self):
        return [
            CameraDataType('trodes-camera-data-type', self.network_location),
            LFPDataType('trodes-lfp-data-type', self.network_location),
            SpikesDataType('trodes-spike-data-type', self.network_location),
        ]
