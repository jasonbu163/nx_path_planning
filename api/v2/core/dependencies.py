# /api/v1/core/dependencies.py
from fastapi import Depends, Request
# from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session

from models.database import get_db
from api.v2.wcs.services import Services

# 数据库会话依赖
def get_database():
    return Depends(get_db)

# def get_thread_pool(request: Request):
#     """获取线程池的依赖项"""
#     return request.app.state.thread_pool

# def get_services(thread_pool: ThreadPoolExecutor = Depends(get_thread_pool)) -> Services:
#     """获取WCS服务实例的依赖项"""
#     return Services(thread_pool)

# WMS 特定的依赖可以在这里定义
# WCS 特定的依赖也可以在另一个文件中定义