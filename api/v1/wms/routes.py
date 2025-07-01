# api/v1/wms/routes.py
from fastapi import APIRouter, HTTPException
# from services.planner import AStarPlanner
# from services.car_commander import CarCommander
# from services.task_service import TaskService
from sqlalchemy.orm import Session
from api.v1.wms import schemas, services
from api.v1.core.dependencies import get_database

router = APIRouter()

@router.post("/orders/", response_model=schemas.Order)
def create_order(
    order: schemas.OrderCreate,
    db: Session = get_database()
):
    """创建新订单"""
    return services.create_order(db, order)

@router.get("/orders/", response_model=list[schemas.Order])
def get_orders(
    skip: int = 0, 
    limit: int = 100,
    db: Session = get_database()
):
    """获取订单列表"""
    orders = services.get_orders(db, skip=skip, limit=limit)
    return orders

@router.get("/orders/{order_id}", response_model=schemas.Order)
def get_order(
    order_id: int, 
    db: Session = get_database()
):
    """获取订单详情"""
    order = services.get_order(db, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单未找到")
    return order

# 添加更多WMS路由...


# @router.post("/path")
# def generate_path(req: PathRequest):
#     map_grid = [[0]*MAP_SIZE for _ in range(MAP_SIZE)]
#     planner = AStarPlanner(map_grid)
#     path = planner.find_path((req.start_x, req.start_y), (req.goal_x, req.goal_y))
#     if not path:
#         return {"error": "无法到达目标位置"}
#     commander = CarCommander()
#     command = commander.build_command(path)
#     return {"path": path, "command": command}

# @router.post("/task", response_model=TaskOut)
# def create_task(task: TaskCreate, db=Depends(get_db)):
#     return TaskService(db).add_task(task)

# @router.get("/task/next", response_model=TaskOut | dict)
# def get_task(db=Depends(get_db)):
#     task = TaskService(db).get_next_task()
#     return task or {"message": "暂无待执行任务"}

# @router.get("/tasks", response_model=List[TaskOut])
# def list_tasks(db=Depends(get_db)):
#     return db.query(Task).all()
