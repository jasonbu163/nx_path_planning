# app/api/v1/wms/services.py
from sqlalchemy.orm import Session

from app.models.base_model import OrderList as OrderModel
from . import schemas

def create_order(db: Session, order: schemas.OrderCreate):
    """创建新订单服务"""
    db_order = OrderModel(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def get_orders(db: Session, skip: int = 0, limit: int = 100):
    """获取订单列表服务"""
    return db.query(OrderModel).offset(skip).limit(limit).all()

def get_order(db: Session, order_id: int):
    """获取订单详情服务"""
    return db.query(OrderModel).filter(OrderModel.id == order_id).first()

# 添加更多WMS服务函数...