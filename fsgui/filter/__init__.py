from fsgui.filter.lfp.ripple import *
from fsgui.filter.lfp.theta import *
from fsgui.filter.spatial.polygon import *
from fsgui.filter.spatial.rectangle import *
from fsgui.filter.spatial.speed import *
from fsgui.filter.spikes.content import *

class FilterProvider:
    def get_nodes(self):
        return [
            AxisAlignedRectangleFilterType('axis-aligned-rect-filter-type'),
            GeometryFilterType('geometry-filter-type'),
            SpeedFilterType('speed-filter-type'),
            RippleFilterType('ripple-filter-type'),
            ThetaFilterType('theta-filter-type'),
            ContentFilterType('content-filter-type'),
        ]

