# api/v1/wcs/routes.py
from fastapi import APIRouter, HTTPException
# from api.v1.common.custom_handlers import http_exception_handler, unhandled_exception_handler
from api.v1.common.response import StandardResponse
from api.v1.common.decorators import standard_response
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


@router.get("/read/location/{location_id}", response_model=StandardResponse[schemas.Location])
@standard_response
async def get_location_by_id(
    location_id: int,
    db: Session = get_database()
):
    """获取指定位置信息"""
    location = services.get_location_by_id(db, location_id=location_id)
    # if not location:
    #     raise HTTPException(status_code=404, detail="位置未找到")
    if location:    
        return location
    else:
        return StandardResponse.isError(message="位置未找到")


@router.get("/read/floor_info", response_model=StandardResponse[list[schemas.Location]])
@standard_response
async def list_locations(
    start_location: int = 1, 
    end_location: int = 100,
    db: Session = get_database()
):
    """获取指定范围内的库位信息"""
    locations = services.get_location_by_floor(db, start_location=start_location, end_location=end_location)
    # if not locations:
    #     raise HTTPException(status_code=404, detail="未找到指定范围内的库位")
    if locations:
        return locations
    else:
        return StandardResponse.isError(message="未找到指定范围内的库位")
    

@router.post("/control/path")
@standard_response
async def get_path(request: schemas.PathBase):
    """
    根据起点和终点查找最短路径
    """
    try:
        task_path = services.get_path(request.source, request.target)
        return StandardResponse.isSuccess(data=task_path)

    except Exception as e:
        return StandardResponse.isError(message=str(e))


@router.post("/control/car_move_segments")
@standard_response
async def car_move_segments(request: schemas.PathBase):
    """
    根据起点和终点控制车辆移动
    """
    try:
        # 获取任务
        segments = services.get_car_move_segments(request.source, request.target)

        # 返回执行路径
        return StandardResponse.isSuccess(data=segments)

    except Exception as e:
        return StandardResponse.isError(message=str(e))
    
@router.post("/control/good_move_segments")
@standard_response
async def good_move_segments(request: schemas.PathBase):
    """
    根据起点和终点控制车辆移动, 带上货物
    """
    try:
        # 获取任务
        segments = services.get_good_move_segments(request.source, request.target)

        # 返回执行路径
        return StandardResponse.isSuccess(data=segments)

    except Exception as e:
        return StandardResponse.isError(message=str(e))

################# 小车 #################

@router.get("/control/get_car_location")
@standard_response
async def get_car_location():
    """
    获取小车当前位置
    :return: 小车当前位置坐标
    例如：{"current_location": "5,3,1"}
    """
    try:
        # 获取任务
        msg = await services.get_car_current_location()

        # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))
    
@router.post("/control/change_car_location")
@standard_response
async def change_car_location(request: schemas.CarMoveBase):
    """
    修改小车位置
    :param request: 请求体，包含目标位置
    例如：{"target": "6,3,1"}
    目标位置格式为 "x,y,z"，如 "6,3,1"
    """
    try:
        # 获取任务
        msg = await services.change_car_location_by_target(request.target)

        # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))

@router.post("/control/car_move")
@standard_response
async def car_move_control(request: schemas.CarMoveBase):
    """
    目标楼层移动电梯
    """
    try:
        # 获取任务
        msg = await services.car_move_by_target(request.target)

        # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))

@router.post("/control/good_move")
@standard_response
async def good_move_control(request: schemas.CarMoveBase):
    """
    目标楼层移动电梯
    """
    try:
        # 获取任务
        msg = await services.good_move_by_target(request.target)

        # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))


################# 提升机 #################
@router.post("/control/lift")
@standard_response
async def lift_control(request: schemas.LiftBase):
    """
    目标楼层移动电梯
    """
    try:
        # 获取任务
        msg = await services.lift_by_id(request.location_id)

        if msg[0] == True:
            return StandardResponse.isSuccess(message=msg[1])
        else:
            return StandardResponse.isError(message=msg[1])

    except Exception as e:
        return StandardResponse.isError(message=str(e))


################# 输送线 #################
@router.get("/control/task_lift_inband")
@standard_response
async def lift_inband_control():
    """
    物料进入提升机, 入库！！
    """
    try:
        # 获取任务
        msg = await services.task_lift_inband()

        # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))
    
@router.get("/control/task_lift_outband")
@standard_response
async def lift_outband_control():
    """
    物料从提升机移动到库口，出库！
    """
    try:
        # 获取任务
        msg = await services.task_lift_outband()

        # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))


@router.post("/control/task_in_lift")
@standard_response
async def task_in_lift(request: schemas.LiftBase):
    """
    物料从 库内 移动到 电梯 --》 出库！！
    """
    try:
        msg = await services.in_lift(request.location_id)
    # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))

@router.post("/control/task_out_lift")
@standard_response
async def task_out_lift(request: schemas.LiftBase):
    """
    物料从 电梯 移动到 库内 --》 入库！！！
    """
    try:
        msg = await services.out_lift(request.location_id)
    # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))
    
@router.post("/control/task_pick_complete")
@standard_response
async def task_pick_complete(request: schemas.LiftBase):
    """
    取走物料完成 --》 入库！！！
    """
    try:
        msg = await services.pick_complete(request.location_id)
    # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))
    
@router.post("/control/task_feed_complete")
@standard_response
async def task_feed_complete(request: schemas.LiftBase):
    """
    放下物料完成 --》 出库！！！
    """
    try:
        msg = await services.feed_complete(request.location_id)
    # 返回执行路径
        return StandardResponse.isSuccess(data=msg)

    except Exception as e:
        return StandardResponse.isError(message=str(e))
    

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