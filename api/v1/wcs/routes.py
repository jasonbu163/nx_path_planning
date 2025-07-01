# api/v1/wcs/routes.py
from fastapi import APIRouter, HTTPException
# from services.planner import AStarPlanner
# from services.car_commander import CarCommander
# from services.task_service import TaskService
from sqlalchemy.orm import Session
from api.v1.wcs import schemas, services
from api.v1.core.dependencies import get_database

router = APIRouter()

@router.post("/tasks/", response_model=schemas.Task)
def create_task(
    task: schemas.TaskCreate, 
    db: Session = get_database()
):
    """创建新任务"""
    return services.create_task(db, task)

@router.get("/tasks/", response_model=list[schemas.Task])
def get_tasks(
    skip: int = 0, 
    limit: int = 100,
    db: Session = get_database()
):
    """获取任务列表"""
    tasks = services.get_tasks(db, skip=skip, limit=limit)
    return tasks

@router.patch("/tasks/{task_id}/status", response_model=schemas.Task)
def update_task_status(
    task_id: str, 
    status_update: schemas.TaskStatusUpdate,
    db: Session = get_database()
):
    """更新任务状态"""
    task = services.update_task_status(db, task_id=task_id, new_status=status_update.status)
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    return task

# 添加更多WCS路由...

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