# app/core/__init__.py
"""
   core/                 # 【核心抽象层】定义所有通用接口和基础数据模型
   ├── exceptions.py     # 自定义异常
   ├── types.py          # 基础数据类型（如DataTag, PLCValue）
   ├── connection.py     # 连接抽象基类（BaseConnection）
   └── client.py         # 客户端抽象基类（BasePLCClient）
"""

from .config import settings
from .database import get_db, DeclarativeBase
from .dependencies import get_database

__all__ = [
    "get_db",
    "DeclarativeBase",
    "get_database",
]