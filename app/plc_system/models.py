# app/plc_system/models.py
from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core import DeclarativeBase


class PLCInfo(DeclarativeBase):
    """PLC设备信息表"""
    __tablename__ = 'plc_information'
    
    id = Column(Integer, primary_key=True)  # 设备ID
    layer = Column(Integer, nullable=False)  # 电梯位置
    task_no = Column(String(50), nullable=False)  # 任务号
    task_type = Column(Integer, nullable=False)  # 任务类型
    status = Column(Integer, default=0)  # 电梯状态