# api/v2/wcs/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Generic, TypeVar, List, Dict, Any

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
        from_attributes = True

# WCS Location Schema
class LocationBase(BaseModel):

    """库位基础模型"""
    location: str = Field(..., examples=["1,1,4"], description="库位坐标")
    status: Optional[str] = Field(
        default="occupied",
        examples=["occupied", "free", "highway", "lift"],
        description="库位状态: free - 可用库位, occupied - 库位已经使用, highway - 过道位置, lift - 为电梯位置"
        )
    pallet_id: Optional[str] = Field(None, examples=["P1001"], description="托盘号")

class LocationID(BaseModel):
    """库位ID"""
    id: Optional[int] = Field(default=1, examples=[1, 2, 3], description="库位ID")


class Locations(BaseModel):
    """库位列表"""
    start_id: int = Field(default=1, examples=[1, 2, 3], description="起始库位ID")
    end_id: int = Field(default=100, examples=[1, 2, 3], description="结束库位ID")

class LocationPosition(BaseModel):
    """库位坐标"""
    location: Optional[str] = Field(default="1,1,4", examples=["1,1,4"], description="库位坐标")

class LocationPallet(BaseModel):
    """托盘号"""
    pallet_id: Optional[str] = Field(..., examples=["P1001"], description="托盘号")

class UpdatePalletByID(LocationID):
    """更新托盘号 - 根据位置ID"""
    new_pallet_id: Optional[str] = Field(..., examples=["P1001"], description="托盘号")

class UpdatePalletByLocation(LocationPosition):
    """更新托盘号 - 根据位置坐标"""
    new_pallet_id: Optional[str] = Field(..., examples=["P1001"], description="托盘号")

class LocationStatus(BaseModel):
    """库位状态"""
    status: Optional[str] = Field(..., examples=["free"], description="新状态")

class UpdateStatusByID(LocationID):
    """更新托盘号 - 根据位置ID"""
    new_status: Optional[str] = Field(..., examples=["free"], description="新状态")

class UpdateStatusByLocation(LocationPosition):
    """更新托盘号 - 根据位置坐标"""
    new_status: Optional[str] = Field(..., examples=["free"], description="新状态")

class BulkUpdatePallets(BaseModel):
    """批量更新托盘号 - 根据位置坐标"""
    updates: List[UpdatePalletByLocation] = Field(
        ...,
        examples=[[{"location": "1,1,1", "new_pallet_id": "P1001"}, {"location": "1,1,2", "new_pallet_id": "P1002"}]], 
        description="更新列表，包含位置和对应的新托盘号"
    )

class BulkDeletePallets(BaseModel):
    """批量删除托盘号 - 根据位置坐标"""
    locations: List[str] = Field(
        ..., 
        examples=[["1,1,1", "1,1,2", "1,1,3"]], 
        description="需要删除托盘号的库位坐标列表"
    )

class BulkSyncLocations(BaseModel):
    """批量同步库位 - 根据位置坐标"""
    data: List[LocationBase] = Field(
        ..., 
        examples=[[{"location": "1,1,1", "status": "free", "pallet_id": None}, {"location": "1,1,2", "status": "occupied", "pallet_id": "P1001"}]], 
        description="需要同步的库位列表"
    )


class GoodTask(BaseModel):
    """WCS带托盘号入库"""
    location: str = Field(..., examples=["1,1,4"], description="库位坐标")
    new_pallet_id: str = Field(..., examples=["P1001"], description="托盘号")

class GoodMoveTask(BaseModel):
    """WCS带托盘号入库"""
    pallet_id: str = Field(..., examples=["P1001"], description="托盘号")
    start_location: str = Field(..., examples=["1,1,4"], description="初始库位坐标")
    end_location: str = Field(..., examples=["1,1,4"], description="目标库位坐标")

class Location(LocationBase):
    """WCS库位模型"""
    id: int
    update_time: datetime = Field(..., examples=["2025-09-29T03:40:02.126657"], description="库位更新时间 (格式为UTC时间)")

    class Config:
        from_attributes = True

# WCS Path
class PathBase(BaseModel):
    """WCS路径基础模型"""
    source: str = Field(..., examples=["1,1,1"], description="起始点")
    target: str = Field(..., examples=["6,3,1"], description="目标点")

class ResponsePathBase(BaseModel):
    """WCS路径模型"""
    path: List[str] = Field(..., examples=[["1,1,1", "1,1,2", "1,1,3", "1,1,4"]], description="路径点列表")

class CarMoveBase(BaseModel):
    """WCS穿梭车基础模型"""
    target: str = Field(..., examples=["6,3,1"], description="目标点")
class CarMove(CarMoveBase):
    task_no: int = Field(..., examples=[1, 2, 3], description="任务号(1-255)")
class GoodMoveBase(BaseModel):
    """WCS穿梭车基础模型"""
    start_location: str = Field(..., examples=["6,3,1"], description="目标点")
    end_location: str = Field(..., examples=["6,3,1"], description="目标点")

class LiftBase(BaseModel):
    """WCS电梯基础模型"""
    layer: int = Field(..., examples=[1, 2, 3], description="电梯楼层")

class DevicesTaskBase(BaseModel):
    """设备任务基础模型"""
    task_no: int = Field(..., examples=[1, 2, 3], description="任务号(1-255)")
    target_layer: int = Field(..., examples=[1, 2, 3, 4], description="任务目标楼层(1-4)")