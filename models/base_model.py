# models/base_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base_enum import TaskStatus, LocationStatus, ERPUploadStatus
from .database import Base

# WCS系统表
class TaskList(Base):
    """WCS-任务表"""
    __tablename__ = 'task_list'
    
    id = Column(String(15), primary_key=True)  # 任务号(年月日时分秒)自动生成
    pallet_id = Column(String(20), nullable=False)  # 托盘号
    location = Column(String(50), nullable=False)  # 仓库位置，格式："x,y,z"
    location_id = Column(Integer, ForeignKey('location_list.id'))  # 新增库位ID外键
    task_type = Column(String(10), nullable=False)  # 任务类型: in=入库; out=出库
    task_status = Column(String(20), default=TaskStatus.PENDING)  # 任务状态
    priority = Column(Integer, default=0)  # 任务优先级: 数字越小越先执行
    creation_time = Column(String(15), nullable=False)  # 创建时间(年月日时分秒)
    
    # 关系
    orders = relationship("OrderList", back_populates="task")

class LocationList(Base):
    """WCS-库位信息表"""
    __tablename__ = 'location_list'
    
    id = Column(Integer, primary_key=True)  # 库位id号
    location = Column(String(50), nullable=False)  # 库位坐标号，格式："x,y,z"
    status = Column(String(20), default=LocationStatus.FREE)  # 库位状态
    pallet_id = Column(String(20))  # 托盘号，可为空
    
    # 关系
    tasks = relationship("TaskList", backref="location_ref", primaryjoin="TaskList.location_id == LocationList.id")

# WMS系统表
class OrderList(Base):
    """WMS-订单表"""
    __tablename__ = 'order_list'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # 订单id(自动生成,自增)
    task_id = Column(String(15), ForeignKey('task_list.id'))  # 关联任务表
    material_code = Column(String(50), nullable=False)  # 物料编码
    material_num = Column(Integer, nullable=False)  # 物料数量
    erp_purchase_id = Column(String(50))  # ERP采购单号
    erp_upload_status = Column(String(20), default=ERPUploadStatus.NOT_UPLOADED)  # ERP上传状态
    pallet_id = Column(String(20))  # 托盘号
    location = Column(String(50))  # 位置
    task_type = Column(String(10))  # 任务类型
    task_status = Column(String(20))  # 任务状态
    creation_time = Column(DateTime, default=func.now())  # 创建时间
    
    # 关系
    task = relationship("TaskList", back_populates="orders")