# models/base_model.py
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_enum import TaskStatus, LocationStatus, ERPUploadStatus
from app.core.database import DeclarativeBase as Base

# WCS系统表
class TaskList(Base):
    """WCS-任务表"""
    __tablename__ = 'task_list'
    
    id: Mapped[str] = mapped_column(String(15), primary_key=True)  # 任务号(年月日时分秒)自动生成
    pallet_id: Mapped[str] = mapped_column(String(20), nullable=False)  # 托盘号
    location: Mapped[str] = mapped_column(String(50), nullable=False)  # 仓库位置，格式："x,y,z"
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('location_list.id'))  # 新增库位ID外键
    task_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 任务类型: in=入库; out=出库
    task_status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING.value)  # 任务状态
    priority: Mapped[int] = mapped_column(Integer, default=0)  # 任务优先级: 数字越小越先执行
    creation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )  # 创建时间(格式为UTC时间)
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )  # 更新时间(格式为UTC时间) 
    
    # 关系
    orders: Mapped[List["OrderList"]] = relationship("OrderList", back_populates="task")

    def __repr__(self) -> str:
        return (f"<TaskList(id='{self.id}', pallet_id='{self.pallet_id}', "
                f"location='{self.location}', task_type='{self.task_type}', "
                f"task_status='{self.task_status}', priority='{self.priority}', "
                f"creation_time='{self.creation_time}')>")


class LocationList(Base):
    """WCS-库位信息表"""
    __tablename__ = 'location_list'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 库位id号
    location: Mapped[str] = mapped_column(String(50), nullable=False)  # 库位坐标号，格式："x,y,z"
    status: Mapped[str] = mapped_column(String(20), default=LocationStatus.FREE.value, nullable=False)  # 库位状态
    pallet_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 托盘号，可为空
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )  # 更新时间(格式为UTC时间) 
    
    # 关系
    tasks: Mapped[List["TaskList"]] = relationship(
        "TaskList",
        backref="location_ref",
        primaryjoin="TaskList.location_id == LocationList.id"
    )

    def __repr__(self) -> str:
        return (f"<LocationList(id='{self.id}', location='{self.location}', "
                f"status='{self.status}', pallet_id='{self.pallet_id}')>")


# WMS系统表
class OrderList(Base):
    """WMS-订单表"""
    __tablename__ = 'order_list'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 订单id(自动生成,自增)
    task_id: Mapped[str] = mapped_column(String(15), ForeignKey('task_list.id'))  # 关联任务表
    material_code: Mapped[str] = mapped_column(String(50), nullable=False)  # 物料编码
    material_num: Mapped[int] = mapped_column(Integer, nullable=False)  # 物料数量
    erp_purchase_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ERP采购单号
    erp_upload_status: Mapped[str] = mapped_column(String(20), default=ERPUploadStatus.NOT_UPLOADED.value)  # ERP上传状态
    pallet_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 托盘号
    location: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 位置
    task_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 任务类型
    task_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 任务状态
    creation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )  # 创建时间(格式为UTC时间)
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )  # 更新时间(格式为UTC时间) 
    
    # 关系
    task: Mapped[List["TaskList"]] = relationship("TaskList", back_populates="orders")

    def __repr__(self) -> str:
        return (f"<OrderList(id='{self.id}', task_id='{self.task_id}', "
                f"material_code='{self.material_code}', material_num='{self.material_num}', "
                f"erp_purchase_id='{self.erp_purchase_id}', erp_upload_status='{self.erp_upload_status}', "
                f"pallet_id='{self.pallet_id}', location='{self.location}', "
                f"task_type='{self.task_type}', task_status='{self.task_status}', "
                f"creation_time='{self.creation_time}')>")