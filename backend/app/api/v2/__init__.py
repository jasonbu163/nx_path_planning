# app/api/v2/init__.py
from .wcs.routes import router as wcs_router
from .wms.routes import router as wms_router

__all__ = ["wcs_router", "wms_router"]