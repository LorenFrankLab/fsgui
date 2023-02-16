from fsgui.filter.lfp.ripple import *
from fsgui.filter.lfp.theta import *
from fsgui.filter.spatial.polygon import *
from fsgui.filter.spatial.rectangle import *
import fsgui.filter.spatial.speed
import fsgui.filter.spatial.binned
import fsgui.filter.spikes.markspace
import fsgui.filter.cluster
import fsgui.filter.arm

class FilterProvider:
    def get_nodes(self):
        return [
            AxisAlignedRectangleFilterType('axis-aligned-rect-filter-type'),
            GeometryFilterType('geometry-filter-type'),
            fsgui.filter.spatial.speed.SpeedFilterType('speed-filter-type'),
            RippleFilterType('ripple-filter-type'),
            ThetaFilterType('theta-filter-type'),
            fsgui.filter.spikes.markspace.MarkSpaceEncoderType('mark-space-encoder-type'),
            fsgui.filter.cluster.DecoderType('point-process-encoder-type'),
            fsgui.filter.spatial.binned.LinearBinningFilterType('linear-binning-type'),
            fsgui.filter.arm.ArmFilterType('arm-filter-type'),
        ]

