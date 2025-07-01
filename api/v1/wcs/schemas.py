# api/v1/wcs/schemas.py
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from datetime import datetime
from typing import Optional

class TaskBase(BaseModel):
    pallet_id: Optional[str] = Field(..., examples=["P1001"], description="托盘号")
    location_id: int = Field(..., examples=[1], description="库位ID")
    location: Optional[str] = Field(..., examples=["1,1,4"], description="库位坐标")
    task_type: Optional[str] = Field(..., examples=["IN"], description="任务类型")
    priority: Optional[int] = Field(default=0, examples=[5], description="任务优先级")

class TaskCreate(TaskBase):
    pass

class TaskStatusUpdate(BaseModel):
    status: Optional[str] = Field(..., examples=["COMPLETED"], description="新状态")

class Task(TaskBase):
    id: str
    creation_time: datetime
    task_status: Optional[str]
    
    class Config:
        orm_mode = True