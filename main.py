# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from api.v1.wcs import routes as wcs_v1_routes
from api.v1.wms import routes as wms_v1_routes
from api.v2.wcs import routes as wcs_v2_routes
from api.v2.wms import routes as wms_v2_routes
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
    title="仓库管理系统 API",
    description="WMS/WCS 整合管理系统",
    version="2.0.0",
    openapi_url="/api/v2/openapi.json",
    docs_url="/api/v2/docs",
    redoc_url="/api/v2/redoc",
    # lifespan=lifespan
)

# 包含 WMS 路由 (v1)
app.include_router(
    wms_v1_routes.router,
    prefix="/api/v1/wms",
    tags=["WMS-v1"]
)

# 包含 WCS 路由 (v1)
app.include_router(
    wcs_v1_routes.router,
    prefix="/api/v1/wcs",
    tags=["WCS-v1"]
)

# 包含 WMS 路由 (v2)
app.include_router(
    wms_v2_routes.router,
    prefix="/api/v2/wms",
    tags=["WMS-v2"]
)

# 包含 WCS 路由 (v2)
app.include_router(
    wcs_v2_routes.router,
    prefix="/api/v2/wcs",
    tags=["WCS-v2"]
)


@app.get("/")
def root():
    return {
        "message": "仓库管理系统 API 已启动",
        "documentation": "/api/v2/docs",
        "wms_v1_api": "/api/v1/wms",
        "wcs_v1_api": "/api/v1/wcs",
        "wms_v2_api": "/api/v2/wms",
        "wcs_v2_api": "/api/v2/wcs"
    }

# scheduler = TaskScheduler()
# threading.Thread(target=scheduler.run, daemon=True).start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # 保持此设置即可支持localhost和局域网
        port=8765,
        reload=True,
        workers=1,
        # loop="asyncio",
        # timeout_keep_alive=30,
        # limit_concurrency=100
    )