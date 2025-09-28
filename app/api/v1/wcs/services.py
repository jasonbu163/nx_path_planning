# api/v1/wcs/services.py

from datetime import datetime
from typing import Optional
import time

from sqlalchemy.orm import Session

from app.models.base_model import TaskList as TaskModel
from app.models.base_model import LocationList as LocationModel
from . import schemas
from app.map_core import PathCustom
from app.devices.service_asyncio import DevicesService, DB_11, DB_12
from app.plc_system import plc_enum

path_planner = PathCustom()

PLC_IP = "192.168.8.10"
CAR_IP = "192.168.8.30"
CAR_PORT = 2504
device_service = DevicesService(PLC_IP, CAR_IP, CAR_PORT)

# from config import CAR_IP, CAR_PORT
# from res_protocol_system import HeartbeatManager, NetworkManager, PacketBuilder
# import threading

# network = NetworkManager(CAR_IP, CAR_PORT)
# bulid = PacketBuilder(device_id = 2)
# hbm = HeartbeatManager(network, bulid)
# threading.Thread(target=hbm.start, daemon=True).start()

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

def get_location_by_id(db: Session, location_id: int):
    """根据库位ID获取库位信息服务"""
    location_info = db.query(LocationModel).get(location_id)
    if not location_info:
        return False
    return location_info

def get_location_by_floor(db: Session, start_location: int, end_location: int):
    """根据起始节点获取库位信息服务"""
    location_floor_info = db.query(LocationModel).filter(
        LocationModel.id >= start_location,
        LocationModel.id <= end_location
    ).all()
    if not location_floor_info:
        return False
    return location_floor_info

def get_path(source: str, target: str):
    """获取路径服务"""
    path = path_planner.find_shortest_path(source, target)
    if not path:
        return False
    return path

def get_car_move_segments(source: str, target: str):
    """获取路径任务"""
    segments = path_planner.build_segments(source, target)
    if not segments:
        return False
    return segments

def get_good_move_segments(source: str, target: str):
    """获取路径任务"""
    segments = path_planner.build_pick_task(source, target)
    if not segments:
        return False
    return segments

################# 小车 #################
async def get_car_current_location():
    """
    获取小车当前位置信息
    """
    msg = await device_service.car_current_location(2)

    return msg

async def change_car_location_by_target(target: str):
    """
    改变小车位置
    """
    await device_service.change_car_location(target)
    return "小车指令发送成功！"

async def car_move_by_target(target: str):
    """
    移动小车
    """
    await device_service.car_move(target)
    return "小车指令发送成功！"

async def good_move_by_target(target: str):
    """
    移动货物
    """
    await device_service.good_move(target)
    return "小车指令发送成功！"

################# 提升机 #################
async def lift_by_id(location_id: int):
    """
    移动电梯
    """

    await device_service.async_connect()

    # 任务识别
    lift_running = device_service.read_bit(11, DB_11.RUNNING.value)
    lift_idle = device_service.read_bit(11, DB_11.IDLE.value)
    lift_no_cargo = device_service.read_bit(11, DB_11.NO_CARGO.value)
    lift_has_car = device_service.read_bit(11, DB_11.HAS_CAR.value)
    lift_has_cargo = device_service.read_bit(11, DB_11.HAS_CARGO.value)

    print(f"0:{lift_running} 1:{lift_idle} 2:{lift_no_cargo} 3:{lift_has_car} 4:{lift_has_cargo}")

    # 任务号
    from random import randint
    task_num = randint(1, 99)
    
    if location_id not in [1,2,3,4]:

        return False, "非法输入！！！"
    
    else:
        if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
            device_service.lift_move(plc_enum.LIFT_TASK_TYPE.IDEL, task_num, location_id)
                ######################## 电梯清零 #################################
            # 确认电梯到位后，清除到位状态
            if device_service.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                device_service.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
            
            time.sleep(2)
            await device_service.wait_for_bit_change(11, DB_11.RUNNING.value, 0)
            await device_service.disconnect()
            return True, "提升机运行结束"
        
        elif lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==1:
            device_service.lift_move(plc_enum.LIFT_TASK_TYPE.CAR, task_num, location_id)
            # 确认电梯到位后，清除到位状态
            if device_service.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                device_service.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
            
            time.sleep(2)
            await device_service.wait_for_bit_change(11, DB_11.RUNNING.value, 0)
            await device_service.disconnect()
            return True, "提升机运行结束"

        elif lift_running==0 and lift_idle==1 and lift_no_cargo==0 and lift_has_cargo==1 and lift_has_car==0:
            device_service.lift_move(plc_enum.LIFT_TASK_TYPE.GOOD, task_num, location_id)
            # 确认电梯到位后，清除到位状态
            if device_service.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                device_service.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
            
            time.sleep(2)
            await device_service.wait_for_bit_change(11, DB_11.RUNNING.value, 0)
            await device_service.disconnect()
            return True, "提升机运行结束"
        
        else:
            await device_service.disconnect()
            return False, "非法操作"
        


################# 输送线 #################
async def task_lift_inband():
    """
    货物： 入口 --》 电梯， 入库！！！
    """
    await device_service.async_connect()

    # 执行指令
    device_service.inband()

    # 等待PLC动作完成
    await device_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)

    await device_service.disconnect()

    return "输送线执行完成"


async def task_lift_outband():
    """
    货物：电梯 --》 出口， 出库！！！
    """
    await device_service.async_connect()

    # 执行指令
    device_service.outband()

    # 等待PLC动作完成
    await device_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)

    await device_service.disconnect()
    return "输送线执行完成"

async def feed_complete(floor:int):
    """
    库内 放料 完成信号
    """
    await device_service.async_connect()

    if floor == 1:
        device_service.write_bit(12, DB_12.FEED_COMPLETE_1030.value, 1)
        time.sleep(1)
        if device_service.read_bit(12, DB_12.FEED_COMPLETE_1030.value, 1):
            device_service.write_bit(12, DB_12.FEED_COMPLETE_1030.value, 0)
        
        await device_service.disconnect()
        return f"🚚 {floor}楼 小车放料操作 完成"

    elif floor == 2:
        device_service.write_bit(12, DB_12.FEED_COMPLETE_1040.value, 1)
        time.sleep(1)
        if device_service.read_bit(12, DB_12.FEED_COMPLETE_1040.value, 1):
            device_service.write_bit(12, DB_12.FEED_COMPLETE_1040.value, 0)
        
        await device_service.disconnect()
        return f"🚚 {floor}楼 小车放料操作 完成"
    
    elif floor == 3:
        device_service.write_bit(12, DB_12.FEED_COMPLETE_1050.value, 1)
        time.sleep(1)
        if device_service.read_bit(12, DB_12.FEED_COMPLETE_1050.value, 1):
            device_service.write_bit(12, DB_12.FEED_COMPLETE_1050.value, 0)
    
        await device_service.disconnect()
        return f"🚚 {floor}楼 小车放料操作 完成"
    
    elif floor == 4:
        device_service.write_bit(12, DB_12.FEED_COMPLETE_1060.value, 1)
        time.sleep(1)
        if device_service.read_bit(12, DB_12.FEED_COMPLETE_1060.value, 1):
            device_service.write_bit(12, DB_12.FEED_COMPLETE_1060.value, 0)

        await device_service.disconnect()
        return f"🚚 {floor}楼 小车放料操作 完成"
    
    else:
        await device_service.disconnect()
        return "非法输入！！！"
    
    
async def in_lift(floor:int):
    """
    货物进入电梯
    """
    print("🚚 小车开始执行放料操作")
    await device_service.async_connect()
    
    if floor == 1:
        device_service.write_bit(12, DB_12.FEED_IN_PROGRESS_1030.value, 1)
        
        await device_service.disconnect()
        return "🚚 一楼 小车放料操作 完成"
    
    elif floor == 2:
        device_service.write_bit(12, DB_12.FEED_IN_PROGRESS_1040.value, 1)
        
        await device_service.disconnect()
        return "🚚 二楼 小车放料操作 完成"
    
    elif floor == 3:
        device_service.write_bit(12, DB_12.FEED_IN_PROGRESS_1050.value, 1)
        
        await device_service.disconnect()
        return "🚚 三楼 小车放料操作 完成"
    
    elif floor == 4:
        device_service.write_bit(12, DB_12.FEED_IN_PROGRESS_1060.value, 1)
        
        await device_service.disconnect()
        return "🚚 四楼 小车放料操作 完成"
    
    else:
        await device_service.disconnect()
        return "非法输入！！！"
    
async def pick_complete(floor:int):
    """
    库内 取料 完成信号
    """
    await device_service.async_connect()

    if floor == 1:
        device_service.write_bit(12, DB_12.PICK_COMPLETE_1030.value, 1)
        if device_service.read_bit(12, DB_12.PICK_COMPLETE_1030.value, 1) == 1:
            device_service.write_bit(12, DB_12.PICK_COMPLETE_1030.value, 0)
            
        await device_service.disconnect()
        return "信号发送完成！"

    elif floor == 2:
        device_service.write_bit(12, DB_12.PICK_COMPLETE_1040.value, 1)
        if device_service.read_bit(12, DB_12.PICK_COMPLETE_1040.value, 1) == 1:
            device_service.write_bit(12, DB_12.PICK_COMPLETE_1040.value, 0)
        
        await device_service.disconnect()
        return "信号发送完成！"
    
    elif floor == 3:
        device_service.write_bit(12, DB_12.PICK_COMPLETE_1050.value, 1)
        if device_service.read_bit(12, DB_12.PICK_COMPLETE_1050.value, 1) == 1:
            device_service.write_bit(12, DB_12.PICK_COMPLETE_1050.value, 0)

        await device_service.disconnect()
        return "信号发送完成！"
    
    elif floor == 4:
        device_service.write_bit(12, DB_12.PICK_COMPLETE_1060.value, 1)
        if device_service.read_bit(12, DB_12.PICK_COMPLETE_1060.value, 1) == 1:
            device_service.write_bit(12, DB_12.PICK_COMPLETE_1060.value, 0)

        await device_service.disconnect()
        return "信号发送完成！"

    else:
        return "非法输入！！！"
    
async def out_lift(floor:int):

    """
    货物离开电梯， 进入库内
    """
    await device_service.async_connect()

    # 确认电梯到位后，清除到位状态
    if device_service.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
        device_service.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
    # 开始执行物料入库动作
    
    time.sleep(1)

    if floor == 1:
        device_service.lift_to_everylayer(1)
        
        # 等待plc动作完成
        print("⏳ 等待PLC动作完成...")
        await device_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1030.value, 1)
    
        # 发送小车 取料中信号
        time.sleep(1)
        device_service.write_bit(12, DB_12.PICK_IN_PROGRESS_1030.value, 1)
        
        await device_service.disconnect()
        return f"操作小车，前往 {floor} 楼提升机口（5，3，{floor}）处，取料！！！取料完成后，必须发送“取料完成指令”！！！"
    
    elif floor == 2:
        device_service.lift_to_everylayer(2)
        
        # 等待plc动作完成
        print("⏳ 等待PLC动作完成...")
        await device_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1040.value, 1)
    
        # 发送小车 取料中信号
        time.sleep(1)
        device_service.write_bit(12, DB_12.PICK_IN_PROGRESS_1040.value, 1)
        
        await device_service.disconnect()
        return f"操作小车，前往 {floor} 楼提升机口（5，3，{floor}）处，取料！！！取料完成后，必须发送“取料完成指令”！！！"
    
    elif floor == 3:
        device_service.lift_to_everylayer(3)
        
        # 等待plc动作完成
        print("⏳ 等待PLC动作完成...")
        await device_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1050.value, 1)
    
        # 发送小车 取料中信号
        time.sleep(1)
        device_service.write_bit(12, DB_12.PICK_IN_PROGRESS_1050.value, 1)
        
        await device_service.disconnect()
        return f"操作小车，前往 {floor} 楼提升机口（5，3，{floor}）处，取料！！！取料完成后，必须发送“取料完成指令”！！！"
    
    elif floor == 4:
        device_service.lift_to_everylayer(4)
        
        # 等待plc动作完成
        print("⏳ 等待PLC动作完成...")
        await device_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1060.value, 1)
    
        # 发送小车 取料中信号
        time.sleep(1)
        device_service.write_bit(12, DB_12.PICK_IN_PROGRESS_1060.value, 1)
        
        await device_service.disconnect()        
        return f"操作小车，前往 2 楼提升机口（5，3，{floor}）处，取料！！！取料完成后，必须发送“取料完成指令”！！！"
    
    else:
        await device_service.disconnect()
        return "非法输入！！！"
    
