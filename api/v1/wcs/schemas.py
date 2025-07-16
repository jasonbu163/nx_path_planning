# api/v1/wcs/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Generic, TypeVar

T = TypeVar("T") # 通用类型变量

# WCS Task Schema
class TaskBase(BaseModel):
    """WCS任务基础模型"""
    pallet_id: Optional[str] = Field(..., examples=["P1001"], description="托盘号")
    location_id: int = Field(..., examples=[1], description="库位ID")
    location: Optional[str] = Field(..., examples=["1,1,4"], description="库位坐标")
    task_type: Optional[str] = Field(..., examples=["IN"], description="任务类型")
    priority: Optional[int] = Field(default=0, examples=[5], description="任务优先级")

class TaskCreate(TaskBase):
    """WCS任务创建模型"""
    pass

class TaskStatusUpdate(BaseModel):
    """任务状态更新"""
    status: Optional[str] = Field(..., examples=["COMPLETED"], description="新状态")

class Task(TaskBase):
    """WCS任务模型"""
    id: str
    creation_time: datetime
    task_status: Optional[str]
    
    class Config:
        orm_mode = True

# WCS Location Schema
class LocationBase(BaseModel):
    """库位基础模型"""
    location: str = Field(..., examples=["1,1,4"], description="库位坐标")
    status: Optional[str] = Field(default="FREE", examples=["FREE", "OCCUPIED"], description="库位状态")
    pallet_id: Optional[str] = Field(None, examples=["P1001"], description="托盘号")

class LocationPallet(LocationBase):
    """托盘号修改"""
    new_pallet_id: Optional[str] = Field(..., examples=["P1001"], description="托盘号")

class LocationStatusUpdate(LocationBase):
    """库位状态修改"""
    new_status: Optional[str] = Field(..., examples=["OCCUPIED"], description="新状态")

class Location(LocationBase):
    """WCS库位模型"""
    id: int

    class Config:
        orm_mode = True

# WCS Path
class PathBase(BaseModel):
    """WCS路径基础模型"""
    source: str = Field(..., examples=["1,1,1"], description="起始点")
    target: str = Field(..., examples=["6,3,1"], description="目标点")

class CarMovePath(PathBase):
    """WCS路径模型"""
    path: list[str]

class GoodMovePath(PathBase):
    """WCS路径切割模型"""
    points: list[str]

class CarMoveBase(BaseModel):
    target: str = Field(..., examples=["6,3,1"], description="目标点")

class LiftBase(BaseModel):
    """WCS提升机基础模型"""
    # task_type: int = Field(..., examples=[1, 2, 4], description="任务类型")
    # task_num: int = Field(..., examples=[1, 2, 3], description="任务号")
    location_id: int = Field(..., examples=[1, 2, 3], description="提升机位置ID")

