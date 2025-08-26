# api/v2/wcs/routes.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi import FastAPI
import asyncio
import random

# from api.v1.common.custom_handlers import http_exception_handler, unhandled_exception_handler
from api.v2.common.response import StandardResponse
from api.v2.common.decorators import standard_response, standard_response_sync
# from services.planner import AStarPlanner
# from services.car_commander import CarCommander
# from services.task_service import TaskService
from sqlalchemy.orm import Session
from api.v2.wcs import schemas
from api.v2.wcs.services import Services
from api.v2.core.dependencies import get_database

# 线程池使用以下方法
# from api.v2.core.dependencies import get_database, get_services

router = APIRouter()
services = Services()

#################################################
# 任务接口
#################################################

@router.post("/tasks", response_model=schemas.Task)
@standard_response
async def create_task(
    task: schemas.TaskCreate, 
    db: Session = get_database()
    ):
    """创建新任务"""
    return services.create_task(db, task)

@router.get("/tasks", response_model=list[schemas.Task])
@standard_response
async def get_tasks(
    skip: int = 0, 
    limit: int = 100,
    db: Session = get_database()
    ):
    """获取任务列表"""
    tasks = services.get_tasks(db, skip=skip, limit=limit)
    return tasks

@router.patch("/tasks/{task_id}/status", response_model=schemas.Task)
@standard_response
async def update_task_status(
    task_id: str, 
    status_update: schemas.TaskStatusUpdate,
    db: Session = get_database()
    ):
    """更新任务状态"""
    task = services.update_task_status(db, task_id=task_id, new_status=status_update.status)
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    return task

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

#################################################
# 库位接口
#################################################
    
@router.get("/read/locations", response_model=StandardResponse[list[schemas.Location]])
@standard_response
async def read_locations(
    db: Session = get_database()
    ):
    """
    [读 - 库位信息] 根据所有库位信息
    """
    return services.get_locations(db)
    
@router.post("/read/location", response_model=StandardResponse[schemas.Location])
@standard_response
async def read_location_by_id(
    request: schemas.LocationID,
    db: Session = get_database()
    ):
    """
    [读 - 库位信息] 根据库位ID, 获取指定位置信息
    """

    if request.id is None:
        return StandardResponse.isError(message="库位ID不能为空")
    location = services.get_location_by_id(db, request.id)
    if location:    
        return StandardResponse.isSuccess(data=location)
    else:
        return StandardResponse.isError(message="位置未找到")
    
@router.post("/read/location_by_loc", response_model=StandardResponse[schemas.Location])
@standard_response
async def read_location_by_loc(
    request: schemas.LocationPosition,
    db: Session = get_database()
    ):
    """
    [读 - 库位信息] 根据库位坐标, 获取指定位置信息
    """
    if request.location is None:
        return StandardResponse.isError(message="位置信息不能为空")
    location_info = services.get_location_by_loc(db, request.location)
    if location_info:    
        return location_info
    else:
        return StandardResponse.isError(message="位置未找到")


@router.post("/read/location_by_pallet_id", response_model=StandardResponse[schemas.Location])
@standard_response
async def read_location_by_pallet_id(
    request: schemas.LocationPallet,
    db: Session = get_database()
    ):
    """
    [读 - 库位信息] 根据库位坐标, 获取指定位置信息
    """

    if request.pallet_id is None:
        return StandardResponse.isError(message="托盘号不能为空")
    location_info = services.get_location_by_pallet_id(db, request.pallet_id)
    if location_info:    
        return location_info
    else:
        return StandardResponse.isError(message="未找到托盘")

    
@router.post("/read/location_by_status", response_model=StandardResponse[list[schemas.Location]])
@standard_response
async def read_location_by_status(
    request: schemas.LocationStatus,
    db: Session = get_database()
    ):
    """
    [读 - 库位信息] 根据库位坐标, 获取指定位置信息

    库位状态: 
        free - 可用库位, 
        occupied - 库位已经使用, 
        highway - 过道位置, 
        lift - 为电梯位置
    """
    
    if request.status is None:
        return StandardResponse.isError(message="状态不能为空")
    location_info = services.get_location_by_status(db, request.status)
    if location_info:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message="未找状态节点")


@router.post("/read/floor_info", response_model=StandardResponse[list[schemas.Location]])
@standard_response
async def read_floor_info(
    request: schemas.Locations,
    db: Session = get_database()
    ):
    """
    [读 - 库位信息] 根据库位ID范围, 获取指定范围内的库位信息
    """

    if request.start_id is None or request.end_id is None:
        return StandardResponse.isError(message="参数错误")
    locations = services.get_location_by_start_to_end(db, request.start_id, request.end_id)
    if locations:
        return  StandardResponse.isSuccess(data=locations)
    else:
        return StandardResponse.isError(message="未找到指定范围内的库位")


@router.post("/write/update_pallet_by_id", response_model=StandardResponse[schemas.Location])
@standard_response
async def write_update_pallet_by_id(
    request: schemas.UpdatePalletByID,
    db: Session = get_database()
    ):
    """
    [更新 - 库位信息] - 通过位置ID修改托盘号, 并返回更新库位状态
    """

    if request.id is None:
        return StandardResponse.isError(message="库位ID不能为空")
    
    # 检查new_pallet_id是否为None
    if request.new_pallet_id is None:
        return StandardResponse.isError(message="托盘号不能为空")
        
    location_info = services.get_location_by_id(db, request.id)
    if location_info:
        new_location_info = services.update_pallet_by_id(db, request.id, request.new_pallet_id)
        return StandardResponse.isSuccess(data=new_location_info)
    else:
        return StandardResponse.isError(message="位置未找到")

    
@router.post("/write/delete_pallet_by_id", response_model=StandardResponse[schemas.Location])
@standard_response
async def write_delete_pallet_by_id(
    request: schemas.LocationID,
    db: Session = get_database()
    ):
    """
    [更新 - 库位信息] - 通过位置ID删除托盘号, 并返回更新库位状态
    """

    if request.id is None:
        return StandardResponse.isError(message="库位ID不能为空")
        
    location_info = services.get_location_by_id(db, request.id)
    if location_info:
        new_location_info = services.delete_pallet_by_id(db, request.id)
        return StandardResponse.isSuccess(data=new_location_info)
    else:
        return StandardResponse.isError(message="位置未找到")


@router.post("/write/update_pallet_by_loc", response_model=StandardResponse[schemas.Location])
@standard_response
async def write_update_pallet_by_loc(
    request: schemas.UpdatePalletByLocation,
    db: Session = get_database()
    ):
    """
    [更新 - 库位信息] - 通过位置ID修改托盘号, 并返回更新库位状态
    """

    if request.location is None:
        return StandardResponse.isError(message="库位坐标不能为空")
    
    # 检查new_pallet_id是否为None
    if request.new_pallet_id is None:
        return StandardResponse.isError(message="托盘号不能为空")
        
    location_info = services.get_location_by_loc(db, request.location)
    if location_info:
        new_location_info = services.update_pallet_by_loc(db, request.location, request.new_pallet_id)
        return StandardResponse.isSuccess(data=new_location_info)
    else:
        return StandardResponse.isError(message="位置未找到")

    
@router.post("/write/delete_pallet_by_loc", response_model=StandardResponse[schemas.Location])
@standard_response
async def write_delete_pallet_by_loc(
    request: schemas.LocationPosition,
    db: Session = get_database()
    ):
    """
    [更新 - 库位信息] - 通过位置ID删除托盘号, 并返回更新库位状态
    """

    if request.location is None:
        return StandardResponse.isError(message="库位坐标不能为空")
        
    location_info = services.get_location_by_loc(db, request.location)
    if location_info:
        new_location_info = services.delete_pallet_by_loc(db, request.location)
        return StandardResponse.isSuccess(data=new_location_info)
    else:
        return StandardResponse.isError(message="位置未找到")


#################################################
# 路径接口
#################################################

@router.post("/create/path")
@standard_response
async def get_path(
    request: schemas.PathBase
    ):
    """
    [生成 - 路径] 根据起点和终点查找最短路径
    """

    return await services.get_path(request.source, request.target)


@router.post("/create/car_move_segments")
@standard_response
async def car_move_segments(
    request: schemas.PathBase
    ):
    """
    [生成 - 车移动任务路径] 根据起点和终点控制车辆移动
    """
    return await services.get_car_move_segments(request.source, request.target)

@router.post("/create/good_move_segments")
@standard_response
async def good_move_segments(
    request: schemas.PathBase
    ):
    """
    [生成 - 货物任务路径] 根据起点和终点控制车辆载货移动
    """
    return await services.get_good_move_segments(request.source, request.target)


#################################################
# 穿梭车接口
#################################################

@router.get("/control/get_car_location")
@standard_response
async def get_car_location():
    """
    [读 - 车辆信息] 获取穿梭车当前位置接口

    ::: return :::
        穿梭车当前位置坐标
    """

    msg = await services.get_car_current_location()
    if msg == "error":
        return StandardResponse.isError(message="操作失败，穿梭车可能未连接", data=msg)
    return StandardResponse.isSuccess(data=msg)

    
@router.post("/control/change_car_location")
@standard_response
async def change_car_location(
    request: schemas.CarMoveBase
    ):
    """
    [更新 - 修改穿梭车位置]

    ::: param ::: 
        request: 请求体
        包含目标位置, 例如：{"target": "6,3,1"}
        目标位置格式为 "x,y,z"，如 "6,3,1"
    """

    msg = await services.change_car_location_by_target(request.target)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败，穿梭车可能未连接", data=msg)
    

@router.post("/control/car_move")
@standard_response
async def car_move_control(
    request: schemas.CarMoveBase
    ):
    """
    [控制 - 穿梭车移动]
    """

    msg = await services.car_move_by_target(request.target)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="发送指令失败", data=msg)


@router.post("/control/good_move")
@standard_response
async def good_move_control(
    request: schemas.CarMoveBase
    ):
    """
    [控制 - 货物移动]
    """

    msg = await services.good_move_by_target(request.target)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="发送指令失败", data=msg)


#################################################
# 电梯接口
#################################################

@router.post("/control/lift")
@standard_response
async def lift_control(
    request: schemas.LiftBase
    ):
    """
    [控制 电梯] 电梯移动至目标楼层
    """
    task_no = random.randint(1, 255)
    msg = await services.lift_by_id(task_no, request.layer)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="找不到该楼层", data=msg)


#################################################
# 输送线接口
#################################################

@router.get("/control/task_lift_inband")
@standard_response
async def lift_inband_control():
    """
    物料进入提升机, 入库！！
    """

    msg = await services.task_lift_inband()
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败", data=msg)
    
@router.get("/control/task_lift_outband")
@standard_response
async def lift_outband_control():
    """
    物料从提升机移动到库口，出库！
    """
    
    msg = await services.task_lift_outband()
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败", data=msg)

@router.post("/control/task_in_lift")
@standard_response
async def task_in_lift(
    request: schemas.LiftBase
    ):
    """
    物料从 库内 移动到 电梯 --》 出库！！
    """
    msg = await services.feed_in_progress(request.layer)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败",data=msg)

@router.post("/control/task_feed_complete")
@standard_response
async def task_feed_complete(
    request: schemas.LiftBase
    ):
    """
    放下物料完成 --》 出库！！！
    """
    msg = await services.feed_complete(request.layer)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败",data=msg)

@router.post("/control/task_out_lift")
@standard_response
async def task_out_lift(
    request: schemas.LiftBase
    ):
    """
    物料从 电梯 移动到 库内 --》 入库！！！
    """
    msg = await services.out_lift(request.layer)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败",data=msg)
    
@router.post("/control/task_pick_complete")
@standard_response
async def task_pick_complete(
    request: schemas.LiftBase
    ):
    """
    取走物料完成 --》 入库！！！
    """
    msg = await services.pick_complete(request.layer)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败",data=msg)

#################################################
# 设备运行监控接口
#################################################

@router.post("/control/wait_car")
@standard_response
async def wait_car(
    request: schemas.CarMoveBase
    ):
    """
    等待设备完成
    """
    msg = await services.wait_car_by_target(request.target)
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败",data=msg)


#################################################
# 出入口二维码接口
#################################################

@router.get("/control/qrcode")
@standard_response
async def qrcode():
    """
    获取二维码
    """
    msg = await services.get_qrcode()
    if msg == False:
        return StandardResponse.isError(message="操作失败", data=msg)
    # return StandardResponse.isSuccess(data=msg)
        

#################################################
# 设备联动接口
#################################################

@router.post("/control/car_cross_layer")
@standard_response
async def control_car_cross_layer(
    request: schemas.LiftBase
    ):
    """
    操作穿梭车联动电梯跨层
    """
    task_no = random.randint(1, 200)
    msg = await services.do_car_cross_layer(
        task_no,
        request.layer
        )
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message=msg[1], data=msg[0])

@router.post("/control/task_inband")
@standard_response
async def control_task_inband(
    request: schemas.CarMoveBase
    ):
    """
    操作穿梭车联动电梯跨层
    """
    task_no = random.randint(1, 200)
    msg = await services.do_task_inband(
        task_no,
        request.target
        )
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message=msg[1], data=msg[0])

@router.post("/control/task_outband")
@standard_response
async def control_task_outband(
    request: schemas.CarMoveBase
    ):
    """
    操作穿梭车联动电梯跨层
    """
    task_no = random.randint(1, 200)
    msg = await services.do_task_outband(
        task_no,
        request.target
        )
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message=msg[1], data=msg[0])