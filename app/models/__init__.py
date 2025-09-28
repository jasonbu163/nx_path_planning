# app/models/__init__.py
from .base_enum import BaseEnum, TaskStatus, TaskType, OrderType, LocationStatus, ERPUploadStatus
from .init_db import init_db
from .init_locations import init_locations

# 导入PLC状态信息模型
from app.plc_system.models import *

# 导入RES状态信息模型
from app.res_system.models import *


__all__ = [
    'BaseEnum',
    'TaskStatus',
    'TaskType',
    'OrderType',
    'LocationStatus',
    'ERPUploadStatus'
]