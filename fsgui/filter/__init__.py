from fsgui.filter.lfp.ripple import *
import fsgui.filter.lfp.ripple_new
from fsgui.filter.lfp.theta import *
from fsgui.filter.lfp.theta_hilbert import *
from fsgui.filter.spatial.polygon import *
from fsgui.filter.spatial.rectangle import *
import fsgui.filter.spatial.speed
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
            fsgui.filter.lfp.ripple_new.RippleFilterType('ripple-new-filter-type'),
            ThetaFilterType('theta-filter-type'),
            fsgui.filter.lfp.theta_hilbert.ThetaPhaseHilbertFilterType('theta-phase-hilbert-filter-type'),
            fsgui.filter.spikes.markspace.MarkSpaceEncoderType('mark-space-encoder-type'),
            fsgui.filter.cluster.DecoderType('point-process-encoder-type'),
            fsgui.filter.arm.ArmFilterType('arm-filter-type'),
        ]

