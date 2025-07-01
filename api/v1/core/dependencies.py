# /api/v1/core/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session

from models.database import get_db

# 数据库会话依赖
def get_database():
    return Depends(get_db)

# WMS 特定的依赖可以在这里定义
# WCS 特定的依赖也可以在另一个文件中定义