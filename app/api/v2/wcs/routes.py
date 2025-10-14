# api/v2/wcs/routes.py
import asyncio
import random
from typing import List, Optional, Any, Union, Dict

from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from fastapi import FastAPI

from app.core.config import settings
# from app.api.v1.common.custom_handlers import http_exception_handler, unhandled_exception_handler
from app.api.v2.common.response import StandardResponse
from app.api.v2.common.decorators import standard_response, standard_response_sync
# from .services.planner import AStarPlanner
# from .services.car_commander import CarCommander
# from .services.task_service import TaskService
from app.api.v2.wcs import schemas
from app.api.v2.wcs.services import TaskServices, LocationServices, PathServices, DeviceServices, InitializationService
from app.api.v2.wcs.device_services_base import DeviceServicesBase
from app.api.v2.core.dependencies import get_database
from app.models import LocationStatus

# 线程池使用以下方法
# from app.api.v2.core.dependencies import get_database, get_services

router = APIRouter()
task_services = TaskServices()
location_services = LocationServices()
path_services = PathServices()
device_services = DeviceServices()
device_services_base = DeviceServicesBase()
initialization_service = InitializationService()

#################################################
# 任务接口
#################################################

# @router.post("/tasks", response_model=schemas.Task)
# @standard_response
# async def create_task(
#     task: schemas.TaskCreate, 
#     db: Session = get_database()
# ):
#     """创建新任务"""
#     return task_services.create_task(db, task)

# @router.get("/tasks", response_model=list[schemas.Task])
# @standard_response
# async def get_tasks(
#     skip: int = 0, 
#     limit: int = 100,
#     db: Session = get_database()
# ):
#     """获取任务列表"""
#     tasks = task_services.get_tasks(db, skip=skip, limit=limit)
#     return tasks

# @router.patch("/tasks/{task_id}/status", response_model=schemas.Task)
# @standard_response
# async def update_task_status(
#     task_id: str, 
#     status_update: schemas.TaskStatusUpdate,
#     db: Session = get_database()
# ):
#     """更新任务状态"""
#     task = task_services.update_task_status(db, task_id=task_id, new_status=status_update.status)
#     if not task:
#         raise HTTPException(status_code=404, detail="任务未找到")
#     return task

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
# 初始化库位接口
#################################################

@router.get("/init/locations", response_model=StandardResponse[List[schemas.Location]])
@standard_response
async def init_locations(
    db: Session = get_database()
) -> StandardResponse[list[schemas.Location]]:
    """初始化库位信息。"""
    
    success, location_info = initialization_service.init_locations(db)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")
    
@router.get("/reset/locations", response_model=StandardResponse[List[schemas.Location]])
@standard_response
async def reset_locations(
    db: Session = get_database()
) -> StandardResponse[list[schemas.Location]]:
    """重置库位信息。"""
    
    success, location_info = initialization_service.reset_to_initial_state(db)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")

#################################################
# 库位接口
#################################################
    
@router.get("/read/locations", response_model=StandardResponse[List[schemas.Location]])
@standard_response
async def read_locations(
    db: Session = get_database()
) -> StandardResponse[list[schemas.Location]]:
    """获取所有库位信息。"""
    
    success, location_info = location_services.get_locations(db)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")
    
@router.post("/read/location_by_id", response_model=StandardResponse[schemas.Location])
@standard_response
async def read_location_by_id(
    request: schemas.LocationID,
    db: Session = get_database()
) -> StandardResponse[schemas.Location]:
    """根据库位ID, 获取指定位置信息。"""

    if request.id is None:
        return StandardResponse.isError(message="库位ID不能为空")
    
    success, location_info = location_services.get_location_by_id(db, request.id)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")
    
@router.post("/read/location_by_loc", response_model=StandardResponse[schemas.Location])
@standard_response
async def read_location_by_loc(
    request: schemas.LocationPosition,
    db: Session = get_database()
) -> StandardResponse[schemas.Location]:
    """根据库位坐标, 获取指定位置信息。"""
    
    if request.location is None:
        return StandardResponse.isError(message="位置信息不能为空")
    
    success, location_info = location_services.get_location_by_loc(db, request.location)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")

@router.post("/read/location_by_pallet_id", response_model=StandardResponse[schemas.Location])
@standard_response
async def read_location_by_pallet_id(
    request: schemas.LocationPallet,
    db: Session = get_database()
) -> StandardResponse[schemas.Location]:
    """根据库位托盘号, 获取指定位置信息。"""

    if request.pallet_id is None:
        return StandardResponse.isError(message="托盘号不能为空")
    
    success, location_info = location_services.get_location_by_pallet_id(db, request.pallet_id)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")

@router.post("/read/location_by_status", response_model=StandardResponse[list[schemas.Location]])
@standard_response
async def read_location_by_status(
    request: schemas.LocationStatus,
    db: Session = get_database()
) -> StandardResponse[list[schemas.Location]]:
    """根据库位状态, 获取指定位置信息。

    - 库位状态: 
        - free - 可用库位, 
        - occupied - 库位已经使用, 
        - highway - 过道位置, 
        - lift - 为电梯位置
    """
    
    LOCATION_STATUS = {
        LocationStatus.FREE.value,
        LocationStatus.OCCUPIED.value,
        LocationStatus.HIGHWAY.value,
        LocationStatus.LIFT.value
    }
    if request.status not in LOCATION_STATUS:
        return StandardResponse.isError(message="提交的状态参数错误")

    if request.status is None:
        return StandardResponse.isError(message="状态不能为空")
    
    success, location_info = location_services.get_location_by_status(db, request.status)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")

@router.post("/read/floor_info", response_model=StandardResponse[list[schemas.Location]])
@standard_response
async def read_floor_info(
    request: schemas.Locations,
    db: Session = get_database()
) -> StandardResponse[list[schemas.Location]]:
    """根据库位ID范围, 获取指定范围内的库位信息。"""

    if request.start_id is None or request.end_id is None:
        return StandardResponse.isError(message="参数错误")
    
    success, location_info = location_services.get_location_by_start_to_end(db, request.start_id, request.end_id)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")

@router.post("/write/update_pallet_by_id", response_model=StandardResponse[schemas.Location])
@standard_response
async def write_update_pallet_by_id(
    request: schemas.UpdatePalletByID,
    db: Session = get_database()
) -> StandardResponse[schemas.Location]:
    """通过位置ID修改托盘号, 并返回更新库位状态。"""

    if request.id is None:
        return StandardResponse.isError(message="库位ID不能为空")
    
    # 检查new_pallet_id是否为None
    if request.new_pallet_id is None:
        return StandardResponse.isError(message="托盘号不能为空")

    success, location_info = location_services.update_pallet_by_id(db, request.id, request.new_pallet_id)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")

@router.post("/write/delete_pallet_by_id", response_model=StandardResponse[schemas.Location])
@standard_response
async def write_delete_pallet_by_id(
    request: schemas.LocationID,
    db: Session = get_database()
) -> StandardResponse[schemas.Location]:
    """通过位置ID删除托盘号, 并返回更新库位状态。"""

    if request.id is None:
        return StandardResponse.isError(message="库位ID不能为空")
        
    success, location_info = location_services.delete_pallet_by_id(db, request.id)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")

@router.post("/write/update_pallet_by_loc", response_model=StandardResponse[schemas.Location])
@standard_response
async def write_update_pallet_by_loc(
    request: schemas.UpdatePalletByLocation,
    db: Session = get_database()
) -> StandardResponse[schemas.Location]:
    """通过位置坐标修改托盘号, 并返回更新库位状态。"""

    if request.location is None:
        return StandardResponse.isError(message="库位坐标不能为空")
    
    # 检查new_pallet_id是否为None
    if request.new_pallet_id is None:
        return StandardResponse.isError(message="托盘号不能为空")
        
    success, location_info = location_services.update_pallet_by_loc(db, request.location, request.new_pallet_id)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")
    
@router.post("/write/bulk_update_pallets", response_model=StandardResponse[List[schemas.Location]])
@standard_response
async def write_bulk_update_pallets(
    request: schemas.BulkUpdatePallets,
    db: Session = get_database()
) -> StandardResponse[List[schemas.Location]]:
    """批量更新托盘号, 并返回更新库位状态。"""

    # 将请求数据转换为服务层需要的格式
    updates = [
        {"location": item.location, "new_pallet_id": item.new_pallet_id}
        for item in request.updates
    ]
        
    success, location_info = location_services.bulk_update_pallets(db, updates)

    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")
    
@router.post("/write/delete_pallet_by_loc", response_model=StandardResponse[schemas.Location])
@standard_response
async def write_delete_pallet_by_loc(
    request: schemas.LocationPosition,
    db: Session = get_database()
) -> StandardResponse[schemas.Location]:
    """通过位置ID删除托盘号, 并返回更新库位状态。"""

    if request.location is None:
        return StandardResponse.isError(message="库位坐标不能为空")
        
    success, location_info = location_services.delete_pallet_by_loc(db, request.location)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")
    
@router.post("/write/bulk_delete_pallets", response_model=StandardResponse[List[schemas.Location]])
@standard_response
async def write_bulk_delete_pallets(
    request: schemas.BulkDeletePallets,
    db: Session = get_database()
) -> StandardResponse[List[schemas.Location]]:
    """批量删除托盘号, 并返回更新库位状态。"""
        
    success, location_info = location_services.bulk_delete_pallets(db, request.locations)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")
    
@router.post("/write/bulk_sync_locations", response_model=StandardResponse[List[schemas.Location]])
@standard_response
async def write_bulk_sync_locations(
    request: schemas.BulkSyncLocations,
    db: Session = get_database()
) -> StandardResponse[List[schemas.Location]]:
    """批量同步库位信息, 并返回更新库位状态。"""

    # 将请求数据转换为服务层需要的格式
    locations = [
        {"location": item.location, "status": item.status, "pallet_id": item.pallet_id}
        for item in request.data
    ]

    success, location_info = location_services.bulk_sync_locations(db, locations)
    
    if success:    
        return StandardResponse.isSuccess(data=location_info)
    else:
        return StandardResponse.isError(message=f"{location_info}")


#################################################
# 路径接口
#################################################

@router.post("/create/path", response_model=StandardResponse[Union[List, Dict]])
@standard_response
async def create_path(request: schemas.PathBase) -> StandardResponse[Union[List, Dict]]:
    """生成路径。根据起点和终点查找最短路径。"""

    success, path_info = await path_services.get_path(request.source, request.target)

    if success:    
        return StandardResponse.isSuccess(data=path_info)
    else:
        return StandardResponse.isError(message=f"{path_info}")

@router.post("/create/car_move_segments", response_model=StandardResponse[Union[List, Dict]])
@standard_response
async def car_move_segments(request: schemas.PathBase) -> StandardResponse[Union[List, Dict]]:
    """生成车移动任务路径。根据起点和终点控制车辆移动。"""

    success, path_info = await path_services.get_car_move_segments(request.source, request.target)

    if success:    
        return StandardResponse.isSuccess(data=path_info)
    else:
        return StandardResponse.isError(message=f"{path_info}")

@router.post("/create/good_move_segments", response_model=StandardResponse[Union[List, Dict]])
@standard_response
async def good_move_segments(request: schemas.PathBase) -> StandardResponse[Union[List, Dict]]:
    """生成货物任务路径。根据起点和终点控制车辆载货移动。"""

    success, path_info = await path_services.get_good_move_segments(request.source, request.target)

    if success:    
        return StandardResponse.isSuccess(data=path_info)
    else:
        return StandardResponse.isError(message=f"{path_info}")


#################################################
# 穿梭车接口
#################################################

@router.get("/control/get_car_location", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def get_car_location() -> StandardResponse[Union[str, Dict]]:
    """获取穿梭车当前位置。"""

    if settings.USE_MOCK_PLC:
        if settings.MOCK_BOOL:
            success = True
            car_info = "4,1,1"
        else:
            success = False
            car_info = "error"
    else:
        success, car_info = device_services_base.get_car_current_location()

    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info}", data=car_info)
    
@router.get("/control/get_car_status", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def get_car_status() -> StandardResponse[Union[str, Dict]]:
    """获取穿梭车当前状态信息。"""

    if settings.USE_MOCK_PLC:
        if settings.MOCK_BOOL:
            success = True
            car_info = {
                'car_status': 1,
                'name': "任务执行中",
                'description': "无警告"
            }
        else:
            success = False
            car_info = {
                'car_status': "error",
                'name': "error",
                'description': "error"
            }
    else:
        success, car_info = device_services_base.get_car_status()

    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info.get('car_status')}", data=car_info)

@router.get("/control/get_car_info_with_power", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def get_car_info_with_power() -> StandardResponse[Union[str, Dict]]:
    """获取穿梭车当前信息（带电量信息）。"""

    if settings.USE_MOCK_PLC:
        if settings.MOCK_BOOL:
            success = True
            car_info = {
                'cmd_no': 96,
                'resluct': 1,
                'current_location': (5, 4, 1),
                'current_segment': 1,
                'cur_barcode': 40401,
                'car_status': '任务执行中',
                'pallet_status': 0,
                'reserve_status': 1,
                'drive_direction': 0,
                'status_description': '无警告',
                'have_pallet': 2,
                'driver_warning': 0,
                'power': 80
            }
        else:
            success = False
            car_info = {
                'cmd_no': 'error',
                'resluct': '心跳发送次数设置错误或未发送心跳！',
                'current_location': 'error',
                'current_segment': 'error',
                'cur_barcode': 'error',
                'car_status': 'error',
                'pallet_status': 'error',
                'reserve_status': 'error',
                'drive_direction': 'error',
                'status_description': 'error',
                'have_pallet': 'error',
                'driver_warning': 'error',
                'power': 'error'
            }
    else:
        success, car_info = device_services_base.get_car_info_with_power()

    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info.get('car_status')}", data=car_info)
    
@router.post("/control/change_car_location", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def change_car_location(
    request: schemas.CarMoveBase
) -> StandardResponse[Union[str, Dict]]:
    """修改穿梭车位置。

    Args:
        - 包含目标位置, 例如：{"target": "6,3,1"}
        - 目标位置格式为 "x,y,z"，如 "6,3,1"
    """

    success, car_info = await device_services.change_car_location_by_target(request.target)
    
    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info}", data=car_info)
    
@router.get("/control/start_car_charge", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def start_car_charge() -> StandardResponse[Union[str, Dict]]:
    """执行穿梭车开始充电指令。"""
    if settings.USE_MOCK_PLC:
        if settings.MOCK_BOOL:
            success = True
            car_info = "[MOCK] ✅ 穿梭车充电指令发送成功"
        else:
            success = False
            car_info = "[MOCK] ❌ 穿梭车充电指令发送失败"
    else:
        success, car_info = await device_services_base.car_charge(is_charge=True)

    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info}", data=car_info)
    
@router.get("/control/stop_car_charge", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def stop_car_charge() -> StandardResponse[Union[str, Dict]]:
    """执行穿梭车结束充电指令。"""
    if settings.USE_MOCK_PLC:
        if settings.MOCK_BOOL:
            success = True
            car_info = "[MOCK] ✅ 穿梭车充电指令发送成功"
        else:
            success = False
            car_info = "[MOCK] ❌ 穿梭车充电指令发送失败"
    else:
        success, car_info = await device_services_base.car_charge(is_charge=False)

    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info}", data=car_info)
    
@router.get("/control/car_move_to_charge", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def car_move_to_charge() -> StandardResponse[Union[str, Dict]]:
    """穿梭车前往充电口充电。"""
    if settings.USE_MOCK_PLC:
        if settings.MOCK_BOOL:
            success = True
            car_info = "[MOCK] ✅ 可以开始执行充电指令"
        else:
            success = False
            car_info = "[MOCK] ❌ 模拟充电失败"
    else:
        success, car_info = await device_services_base.car_move_to_charge()

    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info}", data=car_info)

@router.post("/control/car_move", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def car_move_control(
    request: schemas.CarMoveBase
) -> StandardResponse[Union[str, Dict]]:
    """控制穿梭车移动。"""

    success, car_info = await device_services.car_move_by_target(request.target)
    
    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info}")

@router.post("/control/good_move", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def good_move_control(
    request: schemas.CarMoveBase
) -> StandardResponse[Union[str, Dict]]:
    """控制货物移动。"""

    success, car_info = await device_services.good_move_by_target(request.target)
    
    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info}")

@router.post("/control/good_move_by_start_end_control", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def good_move_by_start_end_control(
    request: schemas.GoodMoveBase
) -> StandardResponse[Union[str, Dict]]:
    """穿梭车到达货物起始位置，再控制货物移动至目标位置。"""

    # success, car_info = await device_services.good_move_by_start_end(request.start_location, request.end_location)
    success, car_info = await device_services_base.good_move_by_start_end(request.start_location, request.end_location)
    
    if success:    
        return StandardResponse.isSuccess(data=car_info)
    else:
        return StandardResponse.isError(message=f"{car_info}")

#################################################
# 电梯接口
#################################################

@router.post("/control/lift", response_model=StandardResponse[Union[str, Dict]])
@standard_response
async def lift_control(
    request: schemas.LiftBase
) -> StandardResponse[Union[str, Dict]]:
    """控制电梯移动至目标楼层。"""
        
    success, lift_info = await device_services.lift_by_id(request.layer)

    if success:
        return StandardResponse.isSuccess(data=lift_info)
    else:
        return StandardResponse.isError(message=f"{lift_info}")

#################################################
# 输送线接口
#################################################

@router.get("/control/task_lift_inband")
@standard_response
async def lift_inband_control():
    """
    物料进入提升机, 入库！！
    """

    msg = await device_services.task_lift_inband()
    if msg:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message="操作失败", data=msg)
    
@router.get("/control/task_lift_outband")
@standard_response
async def lift_outband_control():
    """
    物料从提升机移动到库口，出库！
    """
    
    msg = await device_services.task_lift_outband()
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
    msg = await device_services.feed_in_progress(request.layer)
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
    msg = await device_services.feed_complete(request.layer)
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
    msg = await device_services.out_lift(request.layer)
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
    msg = await device_services.pick_complete(request.layer)
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
    msg = await device_services.get_qrcode()
    if msg == False:
        return StandardResponse.isError(message="操作失败", data=msg)
    return StandardResponse.isSuccess(data=msg)
        

#################################################
# 设备联动接口
#################################################

@router.post("/control/car_cross_layer")
@standard_response
async def control_car_cross_layer(request: schemas.LiftBase):
    """[跨层接口] 操作穿梭车联动电梯跨层。"""
    task_no = random.randint(1, 100)
    success, msg = await device_services_base.do_car_cross_layer(task_no, request.layer)
    if success:
        return StandardResponse.isSuccess(data=msg)
    else:
        return StandardResponse.isError(message=f"{msg}")

@router.post("/control/task_inband")
@standard_response
async def control_task_inband(request: schemas.CarMoveBase):
    """[入库接口] 操作穿梭车联动PLC系统入库 (无障碍检测功能)。"""
    task_no = random.randint(1, 100)
    success, msg = await device_services_base.do_task_inband(task_no, request.target)
    if success:
        return StandardResponse.isSuccess(data=msg)
    else:
        return StandardResponse.isError(message=f"{msg}")

@router.post("/control/task_outband")
@standard_response
async def control_task_outband(request: schemas.CarMoveBase):
    """[出库服务] 操作穿梭车联动PLC系统出库 (无障碍检测功能)。"""
    task_no = random.randint(1, 100)
    success, msg = await device_services_base.do_task_outband(task_no, request.target)
    if success:
        return StandardResponse.isSuccess(data=msg)
    else:
        return StandardResponse.isError(message=f"{msg}")


@router.post("/control/task_inband_with_solve_blocking")
@standard_response
async def control_task_inband_with_solve_blocking(
    request: schemas.GoodTask,
    db: Session = get_database()
    ):
    """[入库服务接口 - 数据库] 操作穿梭车联动PLC系统入库, 使用障碍检测功能。"""
    task_no = random.randint(1, 100)
    success, msg = await device_services_base.do_task_inband_with_solve_blocking(
        task_no,
        request.location,
        request.new_pallet_id,
        db
        )
    if success:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message=f"{msg}")

@router.post("/control/task_outband_with_solve_blocking")
@standard_response
async def control_task_outband_with_solve_blocking(
    request: schemas.GoodTask,
    db: Session = get_database()
    ):
    """[出库服务接口 - 数据库] 操作穿梭车联动PLC系统出库, 使用障碍检测功能。"""
    task_no = random.randint(1, 100)
    success, msg = await device_services_base.do_task_outband_with_solve_blocking(
        task_no,
        request.location,
        request.new_pallet_id,
        db
        )
    if success:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message=f"{msg}")

@router.post("/control/good_move_with_solve_blocking")
@standard_response
async def control_good_move_with_solve_blocking(
    request: schemas.GoodMoveTask,
    db: Session = get_database()
    ):
    """[货物移动服务接口 - 数据库] 操作穿梭车联动PLC系统移动货物, 使用障碍检测功能。"""
    task_no = random.randint(1, 100)
    success, msg = await device_services_base.do_good_move_with_solve_blocking(
        task_no,
        request.pallet_id,
        request.start_location,
        request.end_location,
        db
        )
    if success:
        return StandardResponse.isSuccess(data=msg)
    return StandardResponse.isError(message=f"{msg}")