# main.py
from fastapi import FastAPI
from api.v1.wcs import routes as wcs_routes
from api.v1.wms import routes as wms_routes
from models.database import Base, engine
# from daemon.scheduler import TaskScheduler
import threading

app = FastAPI(
    title="仓库管理系统 API",
    description="WMS/WCS 整合管理系统",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc"
)

# 包含 WMS 路由
app.include_router(
    wms_routes.router,
    prefix="/api/v1/wms",
    tags=["WMS"]
)

# 包含 WCS 路由
app.include_router(
    wcs_routes.router,
    prefix="/api/v1/wcs",
    tags=["WCS"]
)

@app.get("/")
def root():
    return {
        "message": "仓库管理系统 API 已启动",
        "documentation": "/api/v1/docs",
        "wms_api": "/api/v1/wms",
        "wcs_api": "/api/v1/wcs"
    }

# scheduler = TaskScheduler()
# threading.Thread(target=scheduler.run, daemon=True).start()