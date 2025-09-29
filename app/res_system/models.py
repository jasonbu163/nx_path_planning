# app/res_system/models.py
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core import DeclarativeBase


class RESInfo(DeclarativeBase):
    """RES设备信息表"""
    __tablename__ = 'res_information'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 设备ID
    location: Mapped[str] = mapped_column(String(50), nullable=False)  # 穿梭车位置
    task_no: Mapped[str] = mapped_column(String(50), nullable=False)  # 任务号
    task_type: Mapped[str] = mapped_column(Integer, nullable=False)  # 任务类型
    status: Mapped[int] = mapped_column(Integer, default=0)  # 穿梭车状态
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )  # 更新时间(格式为UTC时间) 

    def __repr__(self) -> str:
        return f"<RESInfo(id={self.id}, location='{self.location}', task_no='{self.task_no}', task_type='{self.task_type}', status='{self.status}')>"