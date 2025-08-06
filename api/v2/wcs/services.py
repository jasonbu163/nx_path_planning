# api/v2/wcs/services.py
from datetime import datetime
from typing import Optional
from random import randint
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session
from models.base_model import TaskList as TaskModel
from models.base_model import LocationList as LocationModel
from models.base_enum import LocationStatus
from . import schemas

from map_core import PathCustom
# from devices.service_asyncio import DevicesService, DB_12
from devices.devices_controller import DevicesController
from devices.plc_enum import (
    DB_12,
    DB_11,
    FLOOR_CODE,
    LIFT_TASK_TYPE
)
import config

# from res_protocol_system import HeartbeatManager, NetworkManager, PacketBuilder
# import threading

# network = NetworkManager(CAR_IP, CAR_PORT)
# bulid = PacketBuilder(device_id = 2)
# hbm = HeartbeatManager(network, bulid)
# threading.Thread(target=hbm.start, daemon=True).start()

class Services:

    def __init__(self, thread_pool: ThreadPoolExecutor):
        self.thread_pool = thread_pool
        self._loop = None # 延迟初始化的事件循环引用
        self.path_planner = PathCustom()
        self.device_service = DevicesController(config.PLC_IP, config.CAR_IP, config.CAR_PORT)

    @property
    def loop(self):
        """获取当前运行的事件循环（线程安全）"""
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        return self._loop


    #################################################
    # 任务服务
    #################################################

    def create_task(self, db: Session, task: schemas.TaskCreate):
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

    def get_tasks(self, db: Session, skip: int = 0, limit: int = 100):
        """获取任务列表服务"""
        return db.query(TaskModel).offset(skip).limit(limit).all()

    def update_task_status(self, db: Session, task_id: str, new_status: Optional[str]):
        """更新任务状态服务"""
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            return False
        
        # 使用SQLAlchemy的update方法进行字段更新
        db.query(TaskModel).filter(TaskModel.id == task_id).update({TaskModel.task_status: new_status})
        db.commit()
        db.refresh(task)
        return task

    #################################################
    # 库位服务
    #################################################
    def get_locations(self, db: Session):
        """
        获取所有库位信息服务
        """
        location_floor_info = db.query(LocationModel).all()
        if not location_floor_info:
            return False
        return location_floor_info
    
    def get_location_by_id(self, db: Session, LOCATION_ID: int):
        """
        根据库位ID, 获取库位信息服务
        """
        location_info = db.query(LocationModel).get(LOCATION_ID)
        if not location_info:
            return False
        return location_info

    def get_location_by_loc(self, db: Session, LOCATION: str):
        """
        根据库位坐标, 获取库位信息服务
        """
        location_info = db.query(LocationModel).filter(LocationModel.location == LOCATION).first()
        if not location_info:
            return False
        return location_info

    def get_location_by_pallet_id(self, db: Session, PALLET_ID: str):
        """
        根据托盘号, 获取库位信息
        """
        location_info = db.query(LocationModel).filter(LocationModel.pallet_id == PALLET_ID).first()
        if not location_info:
            return False
        return location_info

    def get_location_by_status(self, db: Session, STATUS: str):
        """
        通过托盘号获取库位信息
        """
        location_info = db.query(LocationModel).filter(LocationModel.status == STATUS).all()
        if not location_info:
            return False
        return location_info

    def get_location_by_start_to_end(self, db: Session, START_ID: int, END_ID: int):
        """
        根据起始节点获取库位信息服务
        """
        location_floor_info = db.query(LocationModel).filter(
            LocationModel.id >= START_ID,
            LocationModel.id <= END_ID
        ).all()
        if not location_floor_info:
            return False
        return location_floor_info

    def update_pallet_by_id(self, db: Session, LOCATION_ID: int, PALLET_ID: str):
        """
        用库位ID, 更新库位托盘号服务
        """
        # Check if location exists
        location_info = db.query(LocationModel).filter(LocationModel.id == LOCATION_ID).first()
        if not location_info:
            return False
        
        # Update pallet ID and status
        db.query(LocationModel).filter(LocationModel.id == LOCATION_ID).update({
            LocationModel.pallet_id: PALLET_ID, 
            LocationModel.status: LocationStatus.OCCUPIED.value
            })
        
        # Commit changes and refresh
        db.commit()
        db.refresh(location_info)
        return location_info

    def delete_pallet_by_id(self, db: Session, LOCATION_ID: int):
        """
        用库位ID, 删除库位托盘号服务
        """
        # Check if location exists
        location_info = db.query(LocationModel).filter(LocationModel.id == LOCATION_ID).first()
        if not location_info:
            return False
        
        # Update pallet ID and status
        db.query(LocationModel).filter(LocationModel.id == LOCATION_ID).update({
            LocationModel.pallet_id: None, 
            LocationModel.status: LocationStatus.FREE.value
            })
        
        # Commit changes and refresh
        db.commit()
        db.refresh(location_info)
        return location_info

    def update_pallet_by_loc(self, db: Session, LOCATION: str, PALLET_ID: str):
        """
        用库位坐标, 更新库位托盘号服务
        """
        # 查询库位信息 匹配是否存在
        location_info = db.query(LocationModel).filter(LocationModel.location == LOCATION).first()
        if not location_info:
            return False
        
        # 写入库位托盘号
        db.query(LocationModel).filter(LocationModel.location == LOCATION).update({
            LocationModel.pallet_id: PALLET_ID,
            LocationModel.status: LocationStatus.OCCUPIED.value
            })

        # Commit changes and refresh
        db.commit()
        db.refresh(location_info)
        return location_info

    def delete_pallet_by_loc(self, db: Session, LOCATION: str):
        """
        用库位ID, 删除库位托盘号服务
        """
        # Check if location exists
        location_info = db.query(LocationModel).filter(LocationModel.location == LOCATION).first()
        if not location_info:
            return False
        
        # Update pallet ID and status
        db.query(LocationModel).filter(LocationModel.location == LOCATION).update({
            LocationModel.pallet_id: None, 
            LocationModel.status: LocationStatus.FREE.value
            })
        
        # Commit changes and refresh
        db.commit()
        db.refresh(location_info)
        return location_info

    #################################################
    # 路径服务
    #################################################

    async def get_path(self, source: str, target: str):
        """
        异步 - 获取路径服务
        """
        path = await self.loop.run_in_executor(
            self.thread_pool,
            self.path_planner.find_shortest_path,
            source, target
            )
        if not path:
            return False
        return path
    
    def _get_path(self, source: str, target: str):
        """
        同步 - 获取路径服务
        """
        path = self.path_planner.find_shortest_path(source, target)
        if not path:
            return False
        return path

    async def get_car_move_segments(self, source: str, target: str):
        """
        异步 - 获取路径任务服务
        """
        segments = await self.loop.run_in_executor(
            self.thread_pool,
            self.path_planner.build_segments,
            source, target
            )

        if not segments:
            return False
        return segments
    
    def _get_car_move_segments(self, source: str, target: str):
        """
        同步 - 获取路径任务服务
        """
        segments = self.path_planner.build_segments(source, target)

        if not segments:
            return False
        return segments
    
    async def get_good_move_segments(self, source: str, target: str):
        """
        异步 - 获取路径任务服务
        """
        segments = await self.loop.run_in_executor(
            self.thread_pool,
            self.path_planner.build_pick_task,
            source, target
            )
        if not segments:
            return False
        return segments

    def _get_good_move_segments(self, source: str, target: str):
        """
        同步 - 获取路径任务服务
        """
        segments = self.path_planner.build_pick_task(source, target)
        if not segments:
            return False
        return segments

    #################################################
    # 穿梭车服务
    #################################################

    def get_car_current_location(self):
        """
        获取穿梭车当前位置信息服务
        """
        msg = self.device_service.car.car_current_location()

        return msg

    def change_car_location_by_target(self, target: str):
        """
        改变穿梭车位置服务
        """
        task_no = randint(1, 255)
        self.device_service.car.change_car_location(task_no, target)
        return "指令发送成功！"

    def car_move_by_target(self, target: str):
        """
        移动穿梭车服务
        """
        task_no = randint(1, 255)
        self.device_service.car.car_move(task_no, target)
        return "指令发送成功！"

    def good_move_by_target(self, target: str):
        """
        移动货物服务
        """
        task_no = randint(1, 255)
        self.device_service.car.good_move(task_no, target)
        return "指令发送成功！"


    #################################################
    # 电梯服务
    #################################################

    async def lift_by_id(self, LAYER: int):
        """
        移动电梯服务
        """

        self.device_service.plc.connect()

        # 任务识别
        lift_running = self.device_service.plc.read_bit(11, DB_11.RUNNING.value)
        lift_idle = self.device_service.plc.read_bit(11, DB_11.IDLE.value)
        lift_no_cargo = self.device_service.plc.read_bit(11, DB_11.NO_CARGO.value)
        lift_has_cargo = self.device_service.plc.read_bit(11, DB_11.HAS_CARGO.value)
        lift_has_car = self.device_service.plc.read_bit(11, DB_11.HAS_CAR.value)

        print(f"[LIFT] 电梯状态 - 电梯运行中:{lift_running} 电梯是否空闲:{lift_idle} 电梯是否无货:{lift_no_cargo} 电梯是否有货:{lift_has_cargo} 电梯是否有车:{lift_has_car} ")

        # 任务号
        task_no = randint(1, 255)
        
        if LAYER not in [1,2,3,4]:

            return False, "非法输入！！！"
        
        else:
            if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
                
                self.device_service.plc.lift_move(LIFT_TASK_TYPE.IDEL, task_no, LAYER)

                await self.device_service.plc.wait_for_bit_change(11, DB_11.RUNNING.value, 0)
                
                # 读取提升机是否空闲
                if self.device_service.plc.read_bit(11, DB_11.IDLE.value):
                    self.device_service.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                time.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.device_service.plc.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.device_service.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                
                self.device_service.plc.disconnect()
                return True, "提升机运行结束"
            
            elif lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==1:
                
                self.device_service.plc.lift_move(LIFT_TASK_TYPE.CAR, task_no, LAYER)
                
                await self.device_service.plc.wait_for_bit_change(11, DB_11.RUNNING.value, 0)
                
                # 读取提升机是否空闲
                if self.device_service.plc.read_bit(11, DB_11.IDLE.value):
                    self.device_service.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                time.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.device_service.plc.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.device_service.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                
                self.device_service.plc.disconnect()
                return True, "提升机运行结束"

            elif lift_running==0 and lift_idle==1 and lift_no_cargo==0 and lift_has_cargo==1 and lift_has_car==0:
                
                self.device_service.plc.lift_move(LIFT_TASK_TYPE.GOOD, task_no, LAYER)
                
                await self.device_service.plc.wait_for_bit_change(11, DB_11.RUNNING.value, 0)
                                
                # 读取提升机是否空闲
                if self.device_service.plc.read_bit(11, DB_11.IDLE.value):
                    self.device_service.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                time.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.device_service.plc.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.device_service.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                
                self.device_service.plc.disconnect()
                return True, "提升机运行结束"
            
            else:
                self.device_service.plc.disconnect()
                return False, "非法操作"
            


    #################################################
    # 输送线服务
    #################################################

    async def task_lift_inband(self):
        """
        货物： 入口 --》 电梯， 入库！！！
        """
        self.device_service.plc.connect()

        # 执行指令
        self.device_service.plc.inband_to_lift()

        # 等待PLC动作完成
        await self.device_service.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)

        self.device_service.plc.disconnect()

        return "输送线执行完成"


    async def task_lift_outband(self):
        """
        货物：电梯 --》 出口， 出库！！！
        """
        self.device_service.plc.connect()

        # 执行指令
        self.device_service.plc.lift_to_outband()

        # 等待PLC动作完成
        await self.device_service.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)

        self.device_service.plc.disconnect()
        return "输送线执行完成"

    def feed_complete(self, LAYER:int):
        """
        库内 放料 完成信号
        """
        self.device_service.plc.connect()

        if LAYER == 1:
            self.device_service.plc.write_bit(12, DB_12.FEED_COMPLETE_1030.value, 1)
            time.sleep(1)
            if self.device_service.plc.read_bit(12, DB_12.FEED_COMPLETE_1030.value, 1):
                self.device_service.plc.write_bit(12, DB_12.FEED_COMPLETE_1030.value, 0)
            
            self.device_service.plc.disconnect()
            return f"🚚 {LAYER}楼 小车放料操作 完成"

        elif LAYER == 2:
            self.device_service.plc.write_bit(12, DB_12.FEED_COMPLETE_1040.value, 1)
            time.sleep(1)
            if self.device_service.plc.read_bit(12, DB_12.FEED_COMPLETE_1040.value, 1):
                self.device_service.plc.write_bit(12, DB_12.FEED_COMPLETE_1040.value, 0)
            
            self.device_service.plc.disconnect()
            return f"🚚 {LAYER}楼 小车放料操作 完成"
        
        elif LAYER == 3:
            self.device_service.plc.write_bit(12, DB_12.FEED_COMPLETE_1050.value, 1)
            time.sleep(1)
            if self.device_service.plc.read_bit(12, DB_12.FEED_COMPLETE_1050.value, 1):
                self.device_service.plc.write_bit(12, DB_12.FEED_COMPLETE_1050.value, 0)
        
            self.device_service.plc.disconnect()
            return f"🚚 {LAYER}楼 小车放料操作 完成"
        
        elif LAYER == 4:
            self.device_service.plc.write_bit(12, DB_12.FEED_COMPLETE_1060.value, 1)
            time.sleep(1)
            if self.device_service.plc.read_bit(12, DB_12.FEED_COMPLETE_1060.value, 1):
                self.device_service.plc.write_bit(12, DB_12.FEED_COMPLETE_1060.value, 0)

            self.device_service.plc.disconnect()
            return f"🚚 {LAYER}楼 小车放料操作 完成"
        
        else:
            self.device_service.plc.disconnect()
            return "非法输入！！！"
        
        
    def in_lift(self, LAYER:int):
        """
        货物进入电梯
        """
        print("🚚 小车开始执行放料操作")
        self.device_service.plc.connect()
        
        if LAYER == 1:
            self.device_service.plc.write_bit(12, DB_12.FEED_IN_PROGRESS_1030.value, 1)
            
            self.device_service.plc.disconnect()
            return "🚚 一楼 小车放料操作 完成"
        
        elif LAYER == 2:
            self.device_service.plc.write_bit(12, DB_12.FEED_IN_PROGRESS_1040.value, 1)
            
            self.device_service.plc.disconnect()
            return "🚚 二楼 小车放料操作 完成"
        
        elif LAYER == 3:
            self.device_service.plc.write_bit(12, DB_12.FEED_IN_PROGRESS_1050.value, 1)
            
            self.device_service.plc.disconnect()
            return "🚚 三楼 小车放料操作 完成"
        
        elif LAYER == 4:
            self.device_service.plc.write_bit(12, DB_12.FEED_IN_PROGRESS_1060.value, 1)
            
            self.device_service.plc.disconnect()
            return "🚚 四楼 小车放料操作 完成"
        
        else:
            self.device_service.plc.disconnect()
            return "非法输入！！！"
        
    def pick_complete(self, LAYER:int):
        """
        库内 取料 完成信号
        """
        self.device_service.plc.connect()

        if LAYER == 1:
            self.device_service.plc.write_bit(12, DB_12.PICK_COMPLETE_1030.value, 1)
            if self.device_service.plc.read_bit(12, DB_12.PICK_COMPLETE_1030.value, 1) == 1:
                self.device_service.plc.write_bit(12, DB_12.PICK_COMPLETE_1030.value, 0)
                
            self.device_service.plc.disconnect()
            return "信号发送完成！"

        elif LAYER == 2:
            self.device_service.plc.write_bit(12, DB_12.PICK_COMPLETE_1040.value, 1)
            if self.device_service.plc.read_bit(12, DB_12.PICK_COMPLETE_1040.value, 1) == 1:
                self.device_service.plc.write_bit(12, DB_12.PICK_COMPLETE_1040.value, 0)
            
            self.device_service.plc.disconnect()
            return "信号发送完成！"
        
        elif LAYER == 3:
            self.device_service.plc.write_bit(12, DB_12.PICK_COMPLETE_1050.value, 1)
            if self.device_service.plc.read_bit(12, DB_12.PICK_COMPLETE_1050.value, 1) == 1:
                self.device_service.plc.write_bit(12, DB_12.PICK_COMPLETE_1050.value, 0)

            self.device_service.plc.disconnect()
            return "信号发送完成！"
        
        elif LAYER == 4:
            self.device_service.plc.write_bit(12, DB_12.PICK_COMPLETE_1060.value, 1)
            if self.device_service.plc.read_bit(12, DB_12.PICK_COMPLETE_1060.value, 1) == 1:
                self.device_service.plc.write_bit(12, DB_12.PICK_COMPLETE_1060.value, 0)

            self.device_service.plc.disconnect()
            return "信号发送完成！"

        else:
            return "非法输入！！！"
        
    async def out_lift(self, LAYER:int):

        """
        货物离开电梯， 进入库内
        """
        self.device_service.plc.connect()

        # 确认电梯到位后，清除到位状态
        if self.device_service.plc.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
            self.device_service.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
        # 开始执行物料入库动作
        
        time.sleep(1)

        if LAYER == 1:
            self.device_service.plc.lift_to_everylayer(1)
            
            # 等待plc动作完成
            print("⏳ 等待PLC动作完成...")
            await self.device_service.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1030.value, 1)
        
            # 发送小车 取料中信号
            time.sleep(1)
            self.device_service.plc.write_bit(12, DB_12.PICK_IN_PROGRESS_1030.value, 1)
            
            self.device_service.plc.disconnect()
            return f"操作小车，前往 {LAYER} 楼提升机口（5，3，{LAYER}）处，取料！！！取料完成后，必须发送“取料完成指令”！！！"
        
        elif LAYER == 2:
            self.device_service.plc.lift_to_everylayer(2)
            
            # 等待plc动作完成
            print("⏳ 等待PLC动作完成...")
            await self.device_service.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1040.value, 1)
        
            # 发送小车 取料中信号
            time.sleep(1)
            self.device_service.plc.write_bit(12, DB_12.PICK_IN_PROGRESS_1040.value, 1)
            
            self.device_service.plc.disconnect()
            return f"操作小车，前往 {LAYER} 楼提升机口（5，3，{LAYER}）处，取料！！！取料完成后，必须发送“取料完成指令”！！！"
        
        elif LAYER == 3:
            self.device_service.plc.lift_to_everylayer(3)
            
            # 等待plc动作完成
            print("⏳ 等待PLC动作完成...")
            await self.device_service.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1050.value, 1)
        
            # 发送小车 取料中信号
            time.sleep(1)
            self.device_service.plc.write_bit(12, DB_12.PICK_IN_PROGRESS_1050.value, 1)
            
            self.device_service.plc.disconnect()
            return f"操作小车，前往 {LAYER} 楼提升机口（5，3，{LAYER}）处，取料！！！取料完成后，必须发送“取料完成指令”！！！"
        
        elif LAYER == 4:
            self.device_service.plc.lift_to_everylayer(4)
            
            # 等待plc动作完成
            print("⏳ 等待PLC动作完成...")
            await self.device_service.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1060.value, 1)
        
            # 发送小车 取料中信号
            time.sleep(1)
            self.device_service.plc.write_bit(12, DB_12.PICK_IN_PROGRESS_1060.value, 1)
            
            self.device_service.plc.disconnect()        
            return f"操作小车，前往 2 楼提升机口（5，3，{LAYER}）处，取料！！！取料完成后，必须发送“取料完成指令”！！！"
        
        else:
            self.device_service.plc.disconnect()
            return "非法输入！！！"
        

    #################################################
    # 出入口二维码服务
    #################################################

    def get_qrcode(self):
        """
        获取入库口二维码
        """
        self.device_service.plc.connect()

        QRcode = self.device_service.plc.scan_qrcode()
        if QRcode is None:
            self.device_service.plc.disconnect()
            return False

        self.device_service.plc.disconnect()
        return QRcode

    #################################################
    # 设备联动服务
    #################################################

    async def do_car_cross_layer(
            self,
            TASK_NO: int,
            TARGET_LAYER: int
            ) -> str:
        """
        操作穿梭车联动电梯跨层
        """

        car_last_location = self.device_service.car_cross_layer(TASK_NO, TARGET_LAYER)

        return car_last_location