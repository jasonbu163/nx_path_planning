# models/base_enum.py
# 枚举基础类型

from enum import Enum

class BaseEnum:
    """枚举基础类型"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class TaskType(str, Enum):
    """任务类型"""
    PUTAWAY = 'in'      # 入库
    PICKING = 'out'      # 出库
    MOVEMENT = 'movement'    # 移库

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = 'waiting'       # 等待执行
    EXECUTING = 'processing'  # 执行中
    COMPLETED = 'completed'   # 执行完成
    FAILED = 'failed'         # 执行失败

class DeviceStatus(str, Enum):
    """设备状态"""
    IDLE = 'IDLE'           # 空闲
    BUSY = 'BUSY'           # 工作中
    ERROR = 'ERROR'         # 错误

class OrderType(str, Enum):
    """订单类型"""
    INBOUND = 'INBOUND'     # 入库单
    OUTBOUND = 'OUTBOUND'   # 出库单

class LocationStatus(str, Enum):
    """库存位置状态"""
    FREE = 'free'             # 空闲
    OCCUPIED = 'occupied'     # 占用
    HIGHWAY = 'highway'       # 过道

class ERPUploadStatus(str, Enum):
    NOT_UPLOADED = 'not_uploaded'   # 未上传
    UPLOADED = 'uploaded'           # 已上传
    FAILED = 'failed'               # 上传失败