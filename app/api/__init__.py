from .v1 import wms_router as v1_wms_router
from .v1 import wcs_router as v1_wcs_router
from .v2 import wms_router as v2_wms_router
from .v2 import wcs_router as v2_wcs_router

__all__ = [
    "v1_wms_router",
    "v1_wcs_router",
    "v2_wms_router",
    "v2_wcs_router"
    ]