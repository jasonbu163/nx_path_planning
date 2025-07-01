# api/v1/wcs/services.py
from sqlalchemy.orm import Session
from models.base_model import TaskList as TaskModel
from . import schemas
from datetime import datetime
from typing import Optional

def create_task(db: Session, task: schemas.TaskCreate):
    """创建新任务服务"""
    task_id = datetime.now().strftime("%Y%m%d%H%M%S")
    creation_time = datetime.now().strftime("%Y%m%d%H%M%S")
    
    db_task = TaskModel(
        id=task_id,
        creation_time=creation_time,
        task_status="waiting",  # 默认等待状态
        **task.dict()
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_tasks(db: Session, skip: int = 0, limit: int = 100):
    """获取任务列表服务"""
    return db.query(TaskModel).offset(skip).limit(limit).all()

def update_task_status(db: Session, task_id: str, new_status: Optional[str]):
    """更新任务状态服务"""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        return False
    
    # 使用SQLAlchemy的update方法进行字段更新
    db.query(TaskModel).filter(TaskModel.id == task_id).update({TaskModel.task_status: new_status})
    db.commit()
    db.refresh(task)
    return task

# 添加更多WCS服务函数...