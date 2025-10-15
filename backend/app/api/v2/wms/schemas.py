# /api/v2/wms/schemas.py
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from datetime import datetime
from typing import Optional

class OrderBase(BaseModel):
    material_code: str = Field(..., examples=["M001"], description="物料编码")
    material_num: int = Field(..., examples=[100], description="物料数量")
    pallet_id: Optional[str] = Field(None, examples=["P1001"], description="托盘号")
    # location_id: Optional[int] = Field(None, examples=[1], description="库位ID")
    location: Optional[str] = Field(None, examples=["1,1,1"], description="库位坐标")

class OrderCreate(OrderBase):
    erp_purchase_id: Optional[str] = Field(default=None, examples=["PO2024001"], description="ERP采购单号")
    
class Order(OrderCreate):
    id: int
    creation_time: datetime
    erp_upload_status: Optional[str]
    
    class Config:
        from_attributes = True