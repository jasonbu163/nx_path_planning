# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from app.core import settings
from app.api import v2_wcs_router

# from daemon.scheduler import TaskScheduler

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # 启动时创建线程池
#     app.state.thread_pool = ThreadPoolExecutor(max_workers=3)
#     print("✅ 线程池已创建")

#     # 这里可以添加其他启动逻辑
#     yield

#     # 关闭时清理资源
#     app.state.thread_pool.shutdown(wait=True)
#     print("⛔ 线程池已关闭")
#     # 这里可以添加其他关闭逻辑


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    # lifespan=lifespan
)

# # 包含 WMS 路由 (v1)
# app.include_router(
#     v1_wms_router,
#     prefix="/api/v1/wms",
#     tags=[f"{settings.PROJECT_NAME}WMS-v1"]
# )

# # 包含 WCS 路由 (v1)
# app.include_router(
#     v1_wcs_router,
#     prefix="/api/v1/wcs",
#     tags=[f"{settings.PROJECT_NAME}WCS-v1"]
# )

# # 包含 WMS 路由 (v2)
# app.include_router(
#     v2_wms_router,
#     prefix="/api/v2/wms",
#     tags=[f"{settings.PROJECT_NAME}WMS-v2"]
# )

# 包含 WCS 路由 (v2)
app.include_router(
    v2_wcs_router,
    prefix="/api/v2/wcs",
    tags=[f"{settings.PROJECT_NAME}WCS-v2"]
)

@app.get("/")
def root():
    return {
        "message": "仓库管理系统 API 已启动",
        "data": {
            "documentation": "/docs",
            "redoc": "/redoc",
            "wcs_v2_api": "/api/v2/wcs"
        }
    }

# scheduler = TaskScheduler()
# threading.Thread(target=scheduler.run, daemon=True).start()