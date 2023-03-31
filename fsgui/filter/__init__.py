import fsgui.filter.lfp.ripple
import fsgui.filter.lfp.ripple_new
import fsgui.filter.lfp.theta
import fsgui.filter.lfp.theta_hilbert
import fsgui.filter.spatial.polygon
import fsgui.filter.spatial.rectangle
import fsgui.filter.spatial.speed
import fsgui.filter.spikes.markspace
import fsgui.filter.cluster
import fsgui.filter.decoder
import fsgui.filter.arm

class FilterProvider:
    def get_nodes(self):
        return [
            fsgui.filter.spatial.rectangle.AxisAlignedRectangleFilterType('axis-aligned-rect-filter-type'),
            fsgui.filter.spatial.polygon.GeometryFilterType('geometry-filter-type'),
            fsgui.filter.spatial.speed.SpeedFilterType('speed-filter-type'),
            fsgui.filter.lfp.ripple.RippleFilterType('ripple-filter-type'),
            fsgui.filter.lfp.ripple_new.RippleFilterType('ripple-new-filter-type'),
            fsgui.filter.lfp.theta.ThetaFilterType('theta-filter-type'),
            fsgui.filter.lfp.theta_hilbert.ThetaPhaseHilbertFilterType('theta-phase-hilbert-filter-type'),
            fsgui.filter.spikes.markspace.MarkSpaceEncoderType('mark-space-encoder-type'),
            fsgui.filter.cluster.DecoderType('point-process-encoder-type'),
            fsgui.filter.arm.ArmFilterType('arm-filter-type'),
            fsgui.filter.decoder.SpikeContentDecoder('spike-content-decoder-type'),
        ]

