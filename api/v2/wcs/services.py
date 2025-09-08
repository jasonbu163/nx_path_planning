# api/v2/wcs/services.py
from datetime import datetime
from typing import Optional
from random import randint
import time
import asyncio
# from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session
from models.base_model import TaskList as TaskModel
from models.base_model import LocationList as LocationModel
from models.base_enum import LocationStatus
from . import schemas

from map_core import PathCustom
# from devices.service_asyncio import DevicesService, DB_12
from devices.devices_controller import DevicesController, AsyncDevicesController, DevicesControllerByStep
from devices.car_controller import AsyncCarController, AsyncSocketCarController
from devices.plc_controller import PLCController
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

    # def __init__(self, thread_pool: ThreadPoolExecutor):
    def __init__(self):
        # self.thread_pool = thread_pool
        self._loop = None # 延迟初始化的事件循环引用
        self.path_planner = PathCustom()
        self.plc_service = PLCController(config.PLC_IP)
        self.car_service = AsyncSocketCarController(config.CAR_IP, config.CAR_PORT)
        self.device_service = DevicesControllerByStep(config.PLC_IP, config.CAR_IP, config.CAR_PORT)

        # 设备操作锁
        self.operation_lock = asyncio.Lock()
        self.operation_in_progress = False

    # @property
    # def loop(self):
    #     """获取当前运行的事件循环（线程安全）"""
    #     if self._loop is None:
    #         self._loop = asyncio.get_running_loop()
    #     return self._loop


    #################################################
    # 电梯锁锁服务
    #################################################

    async def acquire_lock(self):
        """获取电梯操作锁"""
        # 检查锁是否已经被占用
        if self.operation_in_progress:
            return False
            
        acquired = await self.operation_lock.acquire()
        if acquired:
            self.operation_in_progress = True
            return True
        return False

    def release_lock(self):
        """释放电梯操作锁"""
        self.operation_in_progress = False
        if self.operation_lock.locked():
            self.operation_lock.release()

    def is_operation_in_progress(self):
        """检查是否有电梯操作正在进行"""
        return self.operation_in_progress
    
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
        disable_id_list = [
            22, 23, 24, 25, 26, 27, 28, 30, 35,
            63, 64, 65, 66, 67, 68, 69, 71, 76,
            104, 105, 106, 107, 108, 109, 110, 112, 117,
            145, 146, 147, 148, 149, 150, 151, 153, 158
            ]
        if LOCATION_ID in disable_id_list:
            return False
        
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
        disable_id_list = [
            22, 23, 24, 25, 26, 27, 28, 30, 35,
            63, 64, 65, 66, 67, 68, 69, 71, 76,
            104, 105, 106, 107, 108, 109, 110, 112, 117,
            145, 146, 147, 148, 149, 150, 151, 153, 158
            ]
        if LOCATION_ID in disable_id_list:
            return False
        
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
        disable_locations = [
            "4,1,1", "4,2,1", "4,3,1", "4,4,1", "4,5,1", "4,6,1", "4,7,1", "5,3,1", "6,3,1",
            "4,1,2", "4,2,2", "4,3,2", "4,4,2", "4,5,2", "4,6,2", "4,7,2", "5,3,2", "6,3,2",
            "4,1,3", "4,2,3", "4,3,3", "4,4,3", "4,5,3", "4,6,3", "4,7,3", "5,3,3", "6,3,3",
            "4,1,4", "4,2,4", "4,3,4", "4,4,4", "4,5,4", "4,6,4", "4,7,4", "5,3,4", "6,3,4",
            ]
        if LOCATION in disable_locations:
            return False
        
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
        disable_locations = [
            "4,1,1", "4,2,1", "4,3,1", "4,4,1", "4,5,1", "4,6,1", "4,7,1", "5,3,1", "6,3,1",
            "4,1,2", "4,2,2", "4,3,2", "4,4,2", "4,5,2", "4,6,2", "4,7,2", "5,3,2", "6,3,2",
            "4,1,3", "4,2,3", "4,3,3", "4,4,3", "4,5,3", "4,6,3", "4,7,3", "5,3,3", "6,3,3",
            "4,1,4", "4,2,4", "4,3,4", "4,4,4", "4,5,4", "4,6,4", "4,7,4", "5,3,4", "6,3,4",
            ]
        if LOCATION in disable_locations:
            return False
        
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

    # async def get_path(self, source: str, target: str):
    #     """
    #     异步 - 获取路径服务 (线程池)
    #     """
    #     path = await self.loop.run_in_executor(
    #         self.thread_pool,
    #         self.path_planner.find_shortest_path,
    #         source, target
    #         )
    #     if not path:
    #         return False
    #     return path
    
    async def get_path(self, source: str, target: str):
        """
        异步 - 获取路径服务
        """
        path = self.path_planner.find_shortest_path(source, target)
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

    # async def get_car_move_segments(self, source: str, target: str):
    #     """
    #     异步 - 获取路径任务服务 (线程池)
    #     """
    #     segments = await self.loop.run_in_executor(
    #         self.thread_pool,
    #         self.path_planner.build_segments,
    #         source, target
    #         )

    #     if not segments:
    #         return False
    #     return segments

    async def get_car_move_segments(self, source: str, target: str):
        """
        异步 - 获取路径任务服务
        """
        segments = self.path_planner.build_segments(source, target)

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
    
    # async def get_good_move_segments(self, source: str, target: str):
    #     """
    #     异步 - 获取路径任务服务 (线程池)
    #     """
    #     segments = await self.loop.run_in_executor(
    #         self.thread_pool,
    #         self.path_planner.build_pick_task,
    #         source, target
    #         )
    #     if not segments:
    #         return False
    #     return segments

    async def get_good_move_segments(self, source: str, target: str):
        """
        异步 - 获取路径任务服务
        """
        segments = self.path_planner.build_pick_task(source, target)
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

    async def get_car_current_location(self) -> bool | str | None:
        """
        获取穿梭车当前位置信息服务
        """
        msg = await self.car_service.car_current_location()
        # if msg == "error":
        #     return False
        return msg

    async def change_car_location_by_target(self, target: str) -> bool:
        """
        改变穿梭车位置服务
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            task_no = randint(1, 100)
            return await self.car_service.change_car_location(task_no, target)
        
        finally:
            self.release_lock()

    async def car_move_by_target(self, TARGET_LOCATION: str) -> list:
        """
        移动穿梭车服务
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")
        
        try:

            target_loc = list(map(int, TARGET_LOCATION.split(',')))
            target_layer = target_loc[2]
            
            task_no = randint(1, 100)
            lift_move_info = await self.device_service.action_lift_move(task_no, target_layer)
            if lift_move_info[0]:
                self.plc_service.logger.info(f"{lift_move_info[1]}")
                lift_layer_info = await self.device_service.get_lift_layer()
                if lift_layer_info[0] and lift_layer_info[1] == target_layer:
                    self.plc_service.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
                else:
                    self.plc_service.logger.error(f"{lift_layer_info[1]}")
                    return [False, f"{lift_layer_info[1]}"]
            else:
                self.plc_service.logger.error(f"{lift_move_info[1]}")
                return [False, f"{lift_move_info[1]}"]

            # return await self.car_service.car_move(task_no, target)
            return await self.device_service.action_car_move(task_no+1, TARGET_LOCATION)

        finally:
            self.release_lock()

    async def good_move_by_target(self, TARGET_LOCATION: str) -> bool:
        """
        移动货物服务
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")
        try:
            target_loc = list(map(int, TARGET_LOCATION.split(',')))
            target_layer = target_loc[2]
            
            task_no = randint(1, 100)
            lift_move_info = await self.device_service.action_lift_move(task_no, target_layer)
            if lift_move_info[0]:
                self.plc_service.logger.info(f"{lift_move_info[1]}")
                lift_layer_info = await self.device_service.get_lift_layer()
                if lift_layer_info[0] and lift_layer_info[1] == target_layer:
                    self.plc_service.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
                else:
                    self.plc_service.logger.error(f"{lift_layer_info[1]}")
                    # return [False, f"{lift_layer_info[1]}"]
                    return False
            else:
                self.plc_service.logger.error(f"{lift_move_info[1]}")
                # return [False, f"{lift_layer_info[1]}"]
                return False

            return await self.car_service.good_move(task_no+1, TARGET_LOCATION)
        
        finally:
            self.release_lock()
    
    async def good_move_by_start_end(
            self, 
            START_LOCATION: str, 
            END_LOCATION: str
            ) -> list:
        """
        移动货物服务
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")
        try:
            # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
            start_loc = list(map(int, START_LOCATION.split(',')))
            start_layer = start_loc[2]
            end_loc = list(map(int, END_LOCATION.split(',')))
            end_layer = end_loc[2]

            if start_layer != end_layer:
                return [False, "❌ 起点与终点楼层不一致"]
            
            task_no = randint(1, 100)
            lift_move_info = await self.device_service.action_lift_move(task_no, start_layer)
            if lift_move_info[0]:
                self.plc_service.logger.info(f"{lift_move_info[1]}")
                lift_layer_info = await self.device_service.get_lift_layer()
                if lift_layer_info[0] and lift_layer_info[1] == start_layer:
                    self.plc_service.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
                else:
                    self.plc_service.logger.error(f"{lift_layer_info[1]}")
                    return [False, f"{lift_layer_info[1]}"]
            else:
                self.plc_service.logger.error(f"{lift_move_info[1]}")
                return [False, f"{lift_move_info[1]}"]

            task_no = randint(1, 255)
            return await self.device_service.action_good_move(task_no+1, START_LOCATION, END_LOCATION)
        
        finally:
            self.release_lock()


    #################################################
    # 电梯服务
    #################################################

    def _lift_by_id_no_lock(self, TASK_NO: int, LAYER: int) -> bool:
        """
        [同步] 移动电梯服务
        """
        if self.plc_service.connect() and self.plc_service.plc_checker():
            self.plc_service.logger.info("🚧 电梯操作")
            time.sleep(2)
            if self.plc_service._lift_move_by_layer(TASK_NO, LAYER):
                self.plc_service.disconnect()
                return True
            else:
                self.plc_service.disconnect()
                return False
        else:
            self.plc_service.disconnect()
            self.plc_service.logger.error("❌ PLC运行错误")
            return False
    
    async def lift_by_id_no_lock(self, TASK_NO: int, LAYER: int) -> bool:
        """
        [异步] 移动电梯服务
        """
        
        if await self.plc_service.async_connect() and self.plc_service.plc_checker():
            self.plc_service.logger.info("🚧 电梯操作")
            await asyncio.sleep(2)
            if await self.plc_service.lift_move_by_layer(TASK_NO, LAYER):
                await self.plc_service.async_disconnect()
                return True
            else:
                await self.plc_service.async_disconnect()
                return False
        else:
            await self.plc_service.async_disconnect()
            self.plc_service.logger.error("❌ PLC运行错误")
            return False
        
    async def lift_by_id(self, task_no: int, layer: int) -> list:
        """
        控制提升机服务
        """
        # 尝试获取电梯操作锁
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            
            # 调用正确的action_lift_move方法
            return await self.device_service.action_lift_move(task_no, layer)
        
        finally:
            # 释放电梯操作锁
            self.release_lock()


    #################################################
    # 输送线服务
    #################################################

    async def task_lift_inband(self) -> bool:
        """
        [货物 - 入库方向] 入口 -> 电梯
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            if await self.plc_service.async_connect() and self.plc_service.plc_checker():
                self.plc_service.logger.info("📦 货物开始进入电梯...")
                await asyncio.sleep(2)
                self.plc_service.inband_to_lift()

                self.plc_service.logger.info("⏳ 输送线移动中...")
                await self.plc_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)

                self.plc_service.logger.info("✅ 货物到达电梯")
                await self.plc_service.async_disconnect()
                return True
            else:
                await self.plc_service.async_disconnect()
                self.plc_service.logger.error("❌ PLC运行错误")
                return False
        
        finally:
            self.release_lock()


    async def task_lift_outband(self) -> bool:
        """
        [货物 - 出库方向] 电梯 -> 出口
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            if await self.plc_service.async_connect() and self.plc_service.plc_checker():
                self.plc_service.logger.info("📦 货物开始离开电梯...")
                await asyncio.sleep(2)
                self.plc_service.lift_to_outband()

                self.plc_service.logger.info("⏳ 输送线移动中...")
                await self.plc_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)

                self.plc_service.logger.info("✅ 货物到达出口")
                await self.plc_service.async_disconnect()
                return True
            else:
                await self.plc_service.async_disconnect()
                self.plc_service.logger.error("❌ PLC运行错误")
                return False

        finally:
            self.release_lock()
        

    async def feed_in_progress(self, LAYER:int) -> bool:
        """
        [货物 - 出库方向] 货物进入电梯
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            if await self.plc_service.async_connect() and self.plc_service.plc_checker():
                self.plc_service.logger.info(f"📦 开始移动 {LAYER}层 货物到电梯前")
                await asyncio.sleep(2)
                self.plc_service.feed_in_process(LAYER)
                await self.plc_service.async_disconnect()
                return True
            
            else:
                await self.plc_service.async_disconnect()
                self.plc_service.logger.error("❌ PLC运行错误")
                return False
            
        finally:
            self.release_lock()

    async def feed_complete(self, LAYER:int) -> bool:
        """
        [货物 - 出库方向] 库内放货完成信号

        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            if await self.plc_service.async_connect() and self.plc_service.plc_checker():
                self.plc_service.logger.info(f"✅ 货物放置完成")
                await asyncio.sleep(2)
                self.plc_service.feed_complete(LAYER)

                self.plc_service.logger.info(f"🚧 货物进入电梯")
                self.plc_service.logger.info("📦 货物开始进入电梯...")
                
                await asyncio.sleep(1)
                self.plc_service.logger.info("⏳ 输送线移动中...")
                await self.plc_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
                
                self.plc_service.logger.info("✅ 货物到达电梯")
                await self.plc_service.async_disconnect()
                return True
            
            else:
                await self.plc_service.async_disconnect()
                self.plc_service.logger.error("❌ PLC运行错误")
                return False

        finally:
            self.release_lock()
        

    async def out_lift(self, LAYER:int) -> bool:

        """
        [货物 - 入库方向] 货物离开电梯, 进入库内接驳位 (最后附带取货进行中信号发送)
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            if await self.plc_service.async_connect() and self.plc_service.plc_checker():
            
                # 确认电梯到位后，清除到位状态
                self.plc_service.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                if self.plc_service.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.plc_service.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                else:
                    await self.plc_service.async_disconnect()
                    self.plc_service.logger.error("❌ PLC运行错误")
                    return False
                
                await asyncio.sleep(1)
                self.plc_service.logger.info("📦 货物开始进入楼层...")
                self.plc_service.lift_to_everylayer(LAYER)
                    
                self.plc_service.logger.info("⏳ 等待输送线动作完成...")
                # 等待电梯输送线工作结束
                if LAYER == 1:
                    await self.plc_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1030.value, 1)
                elif LAYER == 2:
                    await self.plc_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1040.value, 1)
                elif LAYER == 3:
                    await self.plc_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1050.value, 1)
                elif LAYER == 4:
                    await self.plc_service.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1060.value, 1)
                
                await asyncio.sleep(1)
                self.plc_service.logger.info(f"✅ 货物到达 {LAYER} 层接驳位")
                self.plc_service.logger.info("⌛️ 可以开始取货...")
                await asyncio.sleep(1)
                self.plc_service.pick_in_process(LAYER)
                    
                await self.plc_service.async_disconnect()
                return True
                
            else:
                await self.plc_service.async_disconnect()
                self.plc_service.logger.error("❌ PLC连接失败")
                return False

        finally:
            self.release_lock()

        
    async def pick_complete(self, LAYER:int) -> bool:
        """
        [货物 - 入库方向] 库内取货完成信号
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            if await self.plc_service.async_connect() and self.plc_service.plc_checker():
                self.plc_service.logger.info(f"✅ 货物取货完成")
                await asyncio.sleep(2)
                self.plc_service.pick_complete(LAYER)
                await self.plc_service.async_disconnect()
                return True

            else:
                await self.plc_service.async_disconnect()
                self.plc_service.logger.error("❌ PLC运行错误")
                return False

        finally:
            self.release_lock()

        
    #################################################
    # 设备运行监控服务
    #################################################

    async def wait_car_by_target(self, target: str) -> bool:
        """
        等待穿梭车到达指定位置
        """
        return await self.car_service.wait_car_move_complete_by_location(target)
        

    #################################################
    # 出入口二维码服务
    #################################################

    async def get_qrcode(self):
        """
        获取入库口二维码
        """

        if await self.plc_service.async_connect() and self.plc_service.plc_checker():
            await asyncio.sleep(2)
            QRcode = self.plc_service.scan_qrcode()
            if QRcode is None:
                await self.plc_service.async_disconnect()
                return False

            await self.plc_service.async_disconnect()
            return QRcode
        else:
            await self.plc_service.async_disconnect()
            self.plc_service.logger.error("❌ PLC运行错误")
            return False


    #################################################
    # 设备联动服务
    #################################################

    async def do_car_cross_layer(
            self,
            TASK_NO: int,
            TARGET_LAYER: int
            ) -> list:
        """
        [穿梭车跨层服务] - 操作穿梭车联动电梯跨层
        """

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            car_last_location = await self.device_service.car_cross_layer(
                TASK_NO,
                TARGET_LAYER
                )
            
            if car_last_location[0]:
                return car_last_location[1]
            else:
                return car_last_location

        finally:
            self.release_lock()

        
    async def do_task_inband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
        """
        [入库服务] - 操作穿梭车联动PLC系统入库(无障碍检测)
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            car_last_location = await self.device_service.task_inband(
                TASK_NO,
                TARGET_LOCATION
                )
            
            if car_last_location[0]:
                return car_last_location[1]
            else:
                return car_last_location

        finally:
            self.release_lock()
        
    
    async def do_task_outband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
        """
        [出库服务] - 操作穿梭车联动PLC系统出库(无障碍检测)
        """

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            car_last_location = await self.device_service.task_outband(
                TASK_NO,
                TARGET_LOCATION
                )
            
            if car_last_location[0]:
                return car_last_location[1]
            else:
                return car_last_location

        finally:
            self.release_lock()
        
    def get_block_node(
        self,
        START_LOCATION: str,
        END_LOCATION: str,
        db: Session
        ) -> list:
        """
        [获取阻塞节点] - 用于获取阻塞节点

        ::: params :::
            START_LOCATION: str 路径起点
            END_LOCATION: str 路径终点
            db: Session 数据库会话

        ::: return :::
            阻塞节点列表: list
        """
        
        # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        start_loc = list(map(int, START_LOCATION.split(',')))
        start_layer = start_loc[2]
        end_loc = list(map(int, END_LOCATION.split(',')))
        end_layer = end_loc[2]

        if start_layer != end_layer:
            return [False, "❌ 起点与终点楼层不一致"]
        
        # 获取当前层所有库位信息
        node_status = dict()
        if start_layer == 1:
            all_nodes = self.get_location_by_start_to_end(db, START_ID=124,END_ID=164)
        elif start_layer == 2:
            all_nodes = self.get_location_by_start_to_end(db, START_ID=83,END_ID=123)
        elif start_layer == 3:
            all_nodes = self.get_location_by_start_to_end(db, START_ID=42,END_ID=82)
        elif start_layer == 4:
            all_nodes = self.get_location_by_start_to_end(db, START_ID=1,END_ID=41)
        else:
            self.plc_service.logger.error("❌ 未找到符合条件的库位信息")
            return [False, "❌ 未找到符合条件的库位信息"]
            
        # 检查all_locations是否为False
        if all_nodes:
            # 打印每个位置的详细信息
            for node in all_nodes:
                # print(f"ID: {location.id}, 托盘号: {location.pallet_id}, 坐标: {location.location}, 状态: {location.status}")                        
                # node_status[node.location] = [node.id, node.status, node.pallet_id]
                if node.status in ["lift", "highway"]:
                    continue
                node_status[node.location] = node.status
                
            print(f"[SYSTEM] 第 {start_layer} 层有 {len(node_status)} 个节点")
            # return [True, node_status]
            
            blocking_nodes = self.path_planner.find_blocking_nodes(START_LOCATION, END_LOCATION, node_status)
        
            return [True, blocking_nodes]
                
        else:
            self.plc_service.logger.error("❌ 库位信息获取失败")
            return [False, "❌ 库位信息获取失败"]
            
    async def do_task_inband_with_solve_blocking(
        self,
        TASK_NO: int,
        TARGET_LOCATION: str,
        NEW_PALLET_ID: str,
        db: Session
        ) -> list:
        """
        [入库服务 - 数据库] - 操作穿梭车联动PLC系统入库, 使用障碍检测功能
        """

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            
            self.device_service.logger.info(f"[入库服务 - 数据库] - 操作穿梭车联动PLC系统入库, 使用障碍检测功能")
            
            # ---------------------------------------- #
            # base 1: 获取入库口托盘信息，并校验托盘信息
            # ---------------------------------------- #

            self.device_service.logger.info(f"[base 1] 获取入库口托盘信息，并校验托盘信息")

            sql_qrcode_info = self.get_location_by_pallet_id(db, NEW_PALLET_ID)
            if sql_qrcode_info and sql_qrcode_info.pallet_id in [NEW_PALLET_ID]:
                return [False, "❌ 订单托盘已在库内"]
            self.device_service.logger.info(f"[订单托盘号校验] - ✅ 订单托盘不在库内")
            
            # 获取入库口托盘信息
            qrcode_info = await self.get_qrcode()
            if not qrcode_info:
                return [False, "❌ 获取二维码信息失败"]
            
            # 统一转换为字符串处理
            if isinstance(qrcode_info, bytes):
                try:
                    inband_qrcode_info = qrcode_info.decode('utf-8')
                except UnicodeDecodeError:
                    return [False, "❌ 二维码解码失败"]
            elif isinstance(qrcode_info, str):
                inband_qrcode_info = qrcode_info
            else:
                return [False, "❌ 二维码信息格式无效"]
            
            if NEW_PALLET_ID != inband_qrcode_info:
                return [False, "❌ 订单托盘号和入库口托盘号不一致"]
            self.device_service.logger.info(f"[入口托盘号校验] - ✅ 入口托盘号与订单托盘号一致: {inband_qrcode_info}")
            
            
            # ---------------------------------------- #
            # base 2: 校验订单目标位置
            # ---------------------------------------- #

            self.device_service.logger.info(f"[base 2] 校验订单目标位置")

            buffer_list = [
                "5,1,1", "5,3,1", "5,4,1", "5,5,1",
                "5,1,2", "5,3,2", "5,4,2", "5,5,2",
                "5,1,3", "5,3,3", "5,4,3", "5,5,3",
                "5,1,4", "5,3,4", "5,4,4", "5,5,4"
                ]
            if TARGET_LOCATION in buffer_list:
                return [False, f"❌ {TARGET_LOCATION} 位置为接驳位，不能直接使用此功能操作"]
            location_info = self.get_location_by_loc(db, TARGET_LOCATION)
            if location_info:
                if location_info.status in ["occupied", "lift", "highway"]:
                    return [False, f"❌ 入库目标错误，目标状态为{location_info.status}"]
                else:
                    self.device_service.logger.info(f"[入库位置校验] ✅ 入库位置状态 - {location_info.status}")
                    self.device_service.logger.info(f"[SYSTEM] 入库位置信息 - id:{location_info.id}, 位置:{location_info.location}, 托盘号:{location_info.pallet_id}, 状态:{location_info.status}")
            else:
                return [False, "❌ 目标库位错误"]
            

            # ---------------------------------------- #
            # step 1: 解析目标库位信息
            # ---------------------------------------- #

            self.device_service.logger.info("[step 1] 解析目标库位信息")
            
            target_loc = list(map(int, TARGET_LOCATION.split(',')))
            target_layer = target_loc[2]
            inband_location = f"5,3,{target_layer}"

            
            # ---------------------------------------- #
            # step 2: 判断是否需要穿梭车跨层
            # ---------------------------------------- #

            self.device_service.logger.info("[step 2] 判断是否需要穿梭车跨层")
            
            car_move_info = await self.device_service.car_cross_layer(
                TASK_NO,
                target_layer
                )
            if car_move_info[0]:
                self.device_service.logger.info(f"{car_move_info[1]}")
            else:
                self.device_service.logger.error(f"{car_move_info[1]}")
                return [False, f"{car_move_info[1]}"]
            
            
            # ---------------------------------------- #
            # step 3: 处理入库阻挡货物
            # ---------------------------------------- #

            self.device_service.logger.info("[step 3] 处理入库阻挡货物")

            blocking_nodes = self.get_block_node( inband_location, TARGET_LOCATION, db)
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                # step 3.1: 计算靠近高速道阻塞点(按距离排序)
                # 找到最接近 highway 的阻塞节点
                do_blocking_nodes = []
                # 创建阻塞节点的副本，避免修改原始列表
                remaining_nodes = set(blocking_nodes[1])
                
                # 持续查找并移除最近的节点，直到没有剩余节点
                while remaining_nodes:
                    # 找到最接近 highway 的阻塞节点
                    nearest_highway_node = self.path_planner.find_nearest_highway_node(list(remaining_nodes))
                    if nearest_highway_node:
                        do_blocking_nodes.append(nearest_highway_node)
                        # 从剩余节点中移除已找到的节点
                        remaining_nodes.discard(nearest_highway_node)
                    else:
                        # 如果找不到最近节点，跳出循环避免无限循环
                        break
                        
                self.device_service.logger.info(f"[SYSTEM] 靠近高速道阻塞点(按距离排序): {do_blocking_nodes}")

                # 定义临时存放点
                temp_storage_nodes = [f"5,1,{target_layer}", f"5,4,{target_layer}", f"5,5,{target_layer}"]
                # 记录移动映射关系，用于将货物移回原位
                move_mapping = {}

                # step 3.2: 处理遮挡货物
                block_taskno = TASK_NO+1
                for i, blocking_node in enumerate(do_blocking_nodes):
                    if i < len(temp_storage_nodes):
                        temp_node = temp_storage_nodes[i]
                        self.device_service.logger.info(f"[CAR] 移动({blocking_node})遮挡货物到({temp_node})")
                        move_mapping[blocking_node] = temp_node

                        # 移动货物
                        good_move_info = await self.device_service.action_good_move(block_taskno, blocking_node, temp_node)
                        if good_move_info[0]:
                            self.device_service.logger.info(f"{good_move_info[1]}")
                            block_taskno += 2
                        else:
                            self.device_service.logger.error(f"{good_move_info[1]}")
                            return [False, f"{good_move_info[1]}"]

                    else:
                        self.device_service.logger.warning(f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})")
                        return [False, f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})"]
            else:
                self.device_service.logger.info("[SYSTEM] 无阻塞节点，直接出库")
            

            # ---------------------------------------- #
            # step 4: 货物入库
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 4] 货物入库至位置({TARGET_LOCATION})")
            
            good_move_info = await self.device_service.task_inband(
                TASK_NO+2,
                TARGET_LOCATION
                )
            if good_move_info[0]:
                self.device_service.logger.info(f"货物入库至({TARGET_LOCATION})成功")
            else:
                self.device_service.logger.error(f"货物出库至({TARGET_LOCATION})失败")
                return [False, f"货物出库至({TARGET_LOCATION})失败"]
            
            
            # ---------------------------------------- #
            # step 5: 移动遮挡货物返回到原位（按相反顺序）
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 5] 移动遮挡货物返回到原位（按相反顺序）")
            
            block_taskno = TASK_NO+3
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                for blocking_node, temp_node in reversed(list(move_mapping.items())):
                    self.device_service.logger.info(f"[CAR] 移动({temp_node})遮挡货物返回({blocking_node})")
                    
                    # 移动货物
                    good_move_info = await self.device_service.action_good_move(block_taskno, temp_node, blocking_node)
                    if good_move_info[0]:
                        self.device_service.logger.info(f"{good_move_info[1]}")
                        block_taskno += 2
                    else:
                        self.device_service.logger.error(f"{good_move_info[1]}")
                        return [False, f"{good_move_info[1]}"]
            else:
                self.device_service.logger.info("[SYSTEM] 无阻塞节点返回原位，无需处理")
            
            
            # ---------------------------------------- #
            # step 6: 数据库更新信息
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 6] 数据库更新信息")
            
            update_pallet_id = inband_qrcode_info # 生产用
            # update_pallet_id = NEW_PALLET_ID # 测试用
            
            sql_info = self.update_pallet_by_loc(db, TARGET_LOCATION, update_pallet_id)
            if sql_info:
                sql_returen = {
                    "id": sql_info.id,
                    "location": sql_info.location,
                    "pallet_id": sql_info.pallet_id,
                    "satus": sql_info.status
                }
                return [True, sql_returen]
            else:
                return [False, f"❌ 更新托盘号到({TARGET_LOCATION})失败"]

        finally:
            self.release_lock()
        

    async def do_task_outband_with_solve_blocking(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str,
            NEW_PALLET_ID: str,
            db: Session
            ) -> list:
        """
        [出库服务 - 数据库] - 操作穿梭车联动PLC系统出库, 使用障碍检测功能
        """

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            self.device_service.logger.info(f"[出库服务 - 数据库] - 操作穿梭车联动PLC系统出库, 使用障碍检测功能")
            
            # ---------------------------------------- #
            # base 1: 解析订单托盘信息，并且校验托盘信息
            # ---------------------------------------- #

            self.device_service.logger.info(f"[base 1] 解析订单托盘信息，并且校验托盘信息")

            sql_qrcode_info = self.get_location_by_pallet_id(db, NEW_PALLET_ID)
            if sql_qrcode_info and sql_qrcode_info.pallet_id in [NEW_PALLET_ID]:
                self.device_service.logger.info(f"[订单托盘校验] - ✅ 订单托盘在库内")
            else:
                self.device_service.logger.error(f"[订单托盘校验] - ❌ 订单托盘不在库内")
                return [False, "❌ 订单托盘不在库内"]
            if sql_qrcode_info and sql_qrcode_info.location in [TARGET_LOCATION]:
                self.device_service.logger.error(f"[订单托盘校验] - ✅ 订单托盘位置与库位匹配")
            else:
                self.device_service.logger.error(f"[订单托盘校验] - ❌ 订单托盘位置与库位不匹配")
                return [False, "❌ 订单托盘位置与库位不匹配"]
            
            
            # ---------------------------------------- #
            # base 2: 校验订单目标位置
            # ---------------------------------------- #

            self.device_service.logger.info(f"[base 2] 校验订单目标位置")

            buffer_list = [
                "5,1,1", "5,3,1", "5,4,1", "5,5,1",
                "5,1,2", "5,3,2", "5,4,2", "5,5,2",
                "5,1,3", "5,3,3", "5,4,3", "5,5,3",
                "5,1,4", "5,3,4", "5,4,4", "5,5,4"
                ]
            if TARGET_LOCATION in buffer_list:
                return [False, f"❌ {TARGET_LOCATION} 位置为接驳位/缓冲位，不能使用此功能操作"]
            
            location_info = self.get_location_by_loc(db, TARGET_LOCATION)
            if location_info:
                if location_info.status in ["free", "lift", "highway"]:
                    return [False, f"❌ 出库目标错误，目标状态为{location_info.status}"]
                else:
                    self.device_service.logger.info(f"[出库位置校验] ✅ 出库位置状态 - {location_info.status}")
                    self.device_service.logger.info(f"[SYSTEM] 出库位置信息 - id:{location_info.id}, 位置:{location_info.location}, 托盘号:{location_info.pallet_id}, 状态:{location_info.status}")
            else:
                return [False, "❌ 目标库位错误"]

            
            # ---------------------------------------- #
            # step 1: 解析目标库位信息
            # ---------------------------------------- #

            self.device_service.logger.info("[step 1] 获取目标库位信息")
            
            target_loc = list(map(int, TARGET_LOCATION.split(',')))
            target_layer = target_loc[2]
            outband_location = f"5,3,{target_layer}"

            
            # ---------------------------------------- #
            # step 2: 判断是否需要穿梭车跨层
            # ---------------------------------------- #

            self.device_service.logger.info("[step 2] 先让穿梭车跨层")
            
            car_move_info = await self.device_service.car_cross_layer(
                TASK_NO,
                target_layer
                )
            if car_move_info[0]:
                self.device_service.logger.info(f"{car_move_info[1]}")
            else:
                self.device_service.logger.error(f"{car_move_info[1]}")
                return [False, f"{car_move_info[1]}"]
            
            
            # ---------------------------------------- #
            # step 3: 处理出库阻挡货物
            # ---------------------------------------- #

            self.device_service.logger.info("[step 3] 处理出库阻挡货物")

            blocking_nodes = self.get_block_node(TARGET_LOCATION, outband_location, db)
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                # step 3.1: 计算靠近高速道阻塞点(按距离排序)
                # 找到最接近 highway 的阻塞节点
                do_blocking_nodes = []
                # 创建阻塞节点的副本，避免修改原始列表
                remaining_nodes = set(blocking_nodes[1])
                
                # 持续查找并移除最近的节点，直到没有剩余节点
                while remaining_nodes:
                    # 找到最接近 highway 的阻塞节点
                    nearest_highway_node = self.path_planner.find_nearest_highway_node(list(remaining_nodes))
                    if nearest_highway_node:
                        do_blocking_nodes.append(nearest_highway_node)
                        # 从剩余节点中移除已找到的节点
                        remaining_nodes.discard(nearest_highway_node)
                    else:
                        # 如果找不到最近节点，跳出循环避免无限循环
                        break
                        
                self.device_service.logger.info(f"[SYSTEM] 靠近高速道阻塞点(按距离排序): {do_blocking_nodes}")

                # 定义临时存放点
                temp_storage_nodes = [f"5,1,{target_layer}", f"5,4,{target_layer}", f"5,5,{target_layer}"]
                # 记录移动映射关系，用于将货物移回原位
                move_mapping = {}

                # step 3.2: 处理遮挡货物
                block_taskno = TASK_NO+1
                for i, blocking_node in enumerate(do_blocking_nodes):
                    if i < len(temp_storage_nodes):
                        temp_node = temp_storage_nodes[i]
                        self.device_service.logger.info(f"[CAR] 移动({blocking_node})遮挡货物到({temp_node})")
                        move_mapping[blocking_node] = temp_node

                        # 移动货物
                        good_move_info = await self.device_service.action_good_move(block_taskno, blocking_node, temp_node)
                        if good_move_info[0]:
                            self.device_service.logger.info(f"{good_move_info[1]}")
                            block_taskno += 2
                        else:
                            self.device_service.logger.error(f"{good_move_info[1]}")
                            return [False, f"{good_move_info[1]}"]

                    else:
                        self.device_service.logger.warning(f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})")
                        return [False, f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})"]
            else:
                self.device_service.logger.info("[SYSTEM] 无阻塞节点，直接出库")

            
            # ---------------------------------------- #
            # step 4: 货物出库
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 4] ({TARGET_LOCATION})货物出库")
           
            good_move_info = await self.device_service.task_outband(
                TASK_NO+2,
                TARGET_LOCATION
                )
            if good_move_info[0]:
                self.device_service.logger.info(f"{TARGET_LOCATION}货物出库成功")
            else:
                self.device_service.logger.error(f"{TARGET_LOCATION}货物出库失败")
                return [False, f"{TARGET_LOCATION}货物出库失败"]

            
            # ---------------------------------------- #
            # step 5: 移动遮挡货物返回到原位（按相反顺序）
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 5] 移动遮挡货物返回到原位（按相反顺序）")
            
            block_taskno = TASK_NO+3
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                for blocking_node, temp_node in reversed(list(move_mapping.items())):
                    self.device_service.logger.info(f"[CAR] 移动({temp_node})遮挡货物返回({blocking_node})")
                    
                    # 移动货物
                    good_move_info = await self.device_service.action_good_move(block_taskno, temp_node, blocking_node)
                    if good_move_info[0]:
                        self.device_service.logger.info(f"{good_move_info[1]}")
                        block_taskno += 2
                    else:
                        self.device_service.logger.error(f"{good_move_info[1]}")
                        return [False, f"{good_move_info[1]}"]
            else:
                self.device_service.logger.info("[SYSTEM] 无阻塞节点返回原位，无需处理")
            
            
            # ---------------------------------------- #
            # step 6: 数据库更新信息
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 6] 数据库更新信息")
            
            sql_info = self.delete_pallet_by_loc(db, TARGET_LOCATION)
            if sql_info:
                sql_returen = {
                    "id": sql_info.id,
                    "location": sql_info.location,
                    "pallet_id": sql_info.pallet_id,
                    "satus": sql_info.status
                }
                return [True, sql_returen]
            else:
                return [False, f"❌ 更新托盘号到({TARGET_LOCATION})失败"]

        finally:
            self.release_lock()
        

    async def do_good_move_with_solve_blocking(
            self,
            TASK_NO: int,
            PALLET_ID: str,
            START_LOCATION: str,
            END_LOCATION: str,
            db: Session
            ) -> list:
        """
        [货物移动服务 - 数据库] - 操作穿梭车联动PLC系统移动货物, 使用障碍检测功能
        """

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            self.device_service.logger.info(f"[货物移动服务 - 数据库] - 操作穿梭车联动PLC系统移动货物, 使用障碍检测功能")
            
            # ---------------------------------------- #
            # base 1: 解析订单托盘信息，并且校验托盘信息
            # ---------------------------------------- #

            self.device_service.logger.info(f"[base 1] 解析订单托盘信息，并且校验托盘信息")

            sql_qrcode_info = self.get_location_by_pallet_id(db, PALLET_ID)
            
            if sql_qrcode_info and sql_qrcode_info.pallet_id in [PALLET_ID]:
                self.device_service.logger.info(f"[订单托盘校验] - ✅ 订单托盘在库内")
            else:
                self.device_service.logger.error(f"[订单托盘校验] - ❌ 订单托盘不在库内")
                return [False, "❌ 订单托盘不在库内"]
            
            if sql_qrcode_info and sql_qrcode_info.location in [START_LOCATION]:
                self.device_service.logger.error(f"[订单托盘校验] - ✅ 订单托盘位置与库位匹配")
            else:
                self.device_service.logger.error(f"[订单托盘校验] - ❌ 订单托盘位置与库位不匹配")
                return [False, "❌ 订单托盘位置与库位不匹配"]
            
            
            # ---------------------------------------- #
            # base 2: 校验订单起始位置
            # ---------------------------------------- #

            self.device_service.logger.info(f"[base 2] 校验订单起始位置")

            if START_LOCATION == END_LOCATION:
                return [False, f"❌ 起始位置与目标位置相同({START_LOCATION})，请重新选择"]

            buffer_list = [
                "5,1,1", "5,3,1", "5,4,1", "5,5,1",
                "5,1,2", "5,3,2", "5,4,2", "5,5,2",
                "5,1,3", "5,3,3", "5,4,3", "5,5,3",
                "5,1,4", "5,3,4", "5,4,4", "5,5,4"
                ]
            
            # 校验订单起始位置
            if START_LOCATION in buffer_list:
                return [False, f"❌ {START_LOCATION} 位置为接驳位/缓冲位，不能使用此功能操作"]
            
            location_info = self.get_location_by_loc(db, START_LOCATION)
            if location_info:
                if location_info.status in ["free", "lift", "highway"]:
                    return [False, f"移动目标错误，目标状态为{location_info.status}"]
                else:
                    self.device_service.logger.info(f"[初始位置校验] ✅ 初始位置状态 - {location_info.status}")
                    self.device_service.logger.info(f"[SYSTEM] 初始位置信息 - id:{location_info.id}, 位置:{location_info.location}, 托盘号:{location_info.pallet_id}, 状态:{location_info.status}")
            else:
                return [False, "目标库位错误"]
            
            # 校验订单目标位置
            if END_LOCATION in buffer_list:
                return [False, f"❌ {END_LOCATION} 位置为接驳位/缓冲位，不能使用此功能操作"]
            
            location_info = self.get_location_by_loc(db, END_LOCATION)
            if location_info:
                if location_info.status in ["occupied", "lift", "highway"]:
                    return [False, f"移动目标错误，目标状态为{location_info.status}"]
                else:
                    self.device_service.logger.info(f"[目标位置校验] ✅ 目标位置状态 - {location_info.status}")
                    self.device_service.logger.info(f"[SYSTEM] 目标位置信息 - id:{location_info.id}, 位置:{location_info.location}, 托盘号:{location_info.pallet_id}, 状态:{location_info.status}")
            else:
                return [False, "❌ 目标库位错误"]

            
            # ---------------------------------------- #
            # step 1: 解析目标库位信息
            # ---------------------------------------- #

            self.device_service.logger.info("[step 1] 获取目标库位信息")
            
            # 获取初始库位信息
            start_loc = list(map(int, START_LOCATION.split(',')))
            start_layer = start_loc[2]

            end_loc = list(map(int, END_LOCATION.split(',')))
            end_layer = end_loc[2]

            if start_layer != end_layer:
                return [False, "❌ 初始层与目标层不一致"]

            
            # ---------------------------------------- #
            # step 2: 判断是否需要穿梭车跨层
            # ---------------------------------------- #

            self.device_service.logger.info("[step 2] 先让穿梭车跨层")
            
            car_move_info = await self.device_service.car_cross_layer(
                TASK_NO,
                start_layer
                )
            if car_move_info[0]:
                self.device_service.logger.info(f"{car_move_info[1]}")
            else:
                self.device_service.logger.error(f"{car_move_info[1]}")
                return [False, f"{car_move_info[1]}"]
            
            
            # ---------------------------------------- #
            # step 3: 处理阻挡货物
            # ---------------------------------------- #

            self.device_service.logger.info("[step 3] 处理出库阻挡货物")

            blocking_nodes = self.get_block_node(START_LOCATION, END_LOCATION, db)
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                # step 3.1: 计算靠近高速道阻塞点(按距离排序)
                # 找到最接近 highway 的阻塞节点
                do_blocking_nodes = []
                # 创建阻塞节点的副本，避免修改原始列表
                remaining_nodes = set(blocking_nodes[1])
                
                # 持续查找并移除最近的节点，直到没有剩余节点
                while remaining_nodes:
                    # 找到最接近 highway 的阻塞节点
                    nearest_highway_node = self.path_planner.find_nearest_highway_node(list(remaining_nodes))
                    if nearest_highway_node:
                        do_blocking_nodes.append(nearest_highway_node)
                        # 从剩余节点中移除已找到的节点
                        remaining_nodes.discard(nearest_highway_node)
                    else:
                        # 如果找不到最近节点，跳出循环避免无限循环
                        break
                        
                self.device_service.logger.info(f"[SYSTEM] 靠近高速道阻塞点(按距离排序): {do_blocking_nodes}")
                if len(do_blocking_nodes) > 3:
                    self.device_service.logger.warning(f"❌ 没有足够的临时存储点操作货物移动 ({START_LOCATION}) -> ({END_LOCATION})")
                    return [False, f"❌ 没有足够的临时存储点操作货物移动 ({START_LOCATION}) -> ({END_LOCATION})"]

                # 定义临时存放点
                temp_storage_nodes = [f"5,1,{end_layer}", f"5,4,{end_layer}", f"5,5,{end_layer}"]
                # 记录移动映射关系，用于将货物移回原位
                move_mapping = {}

                # step 3.2: 处理遮挡货物
                block_taskno = TASK_NO+1
                for i, blocking_node in enumerate(do_blocking_nodes):
                    if i < len(temp_storage_nodes):
                        temp_node = temp_storage_nodes[i]
                        self.device_service.logger.info(f"[CAR] 移动({blocking_node})遮挡货物到({temp_node})")
                        move_mapping[blocking_node] = temp_node

                        # 移动货物
                        good_move_info = await self.device_service.action_good_move(block_taskno, blocking_node, temp_node)
                        if good_move_info[0]:
                            self.device_service.logger.info(f"{good_move_info[1]}")
                            block_taskno += 2
                        else:
                            self.device_service.logger.error(f"{good_move_info[1]}")
                            return [False, f"{good_move_info[1]}"]

                    else:
                        self.device_service.logger.warning(f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})")
                        return [False, f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})"]
            else:
                self.device_service.logger.info("[SYSTEM] 无阻塞节点，直接出库")

            
            # ---------------------------------------- #
            # step 4: 货物转移
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 4] ({START_LOCATION})货物转移到({END_LOCATION})")
            
            good_move_info = await self.device_service.action_good_move(
                TASK_NO+2,
                START_LOCATION,
                END_LOCATION
                )
            if good_move_info[0]:
                self.device_service.logger.info(f"✅ ({START_LOCATION})货物转移到({END_LOCATION})成功")
            else:
                self.device_service.logger.error(f"❌ ({START_LOCATION})货物转移到({END_LOCATION})失败")
                return [False, f"❌ ({START_LOCATION})货物转移到({END_LOCATION})失败"]

            
            # ---------------------------------------- #
            # step 5: 移动遮挡货物返回到原位（按相反顺序）
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 5] 移动遮挡货物返回到原位（按相反顺序）")
            
            block_taskno = TASK_NO+3
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                for blocking_node, temp_node in reversed(list(move_mapping.items())):
                    self.device_service.logger.info(f"[CAR] 移动({temp_node})遮挡货物返回({blocking_node})")
                    
                    # 移动货物
                    good_move_info = await self.device_service.action_good_move(block_taskno, temp_node, blocking_node)
                    if good_move_info[0]:
                        self.device_service.logger.info(f"{good_move_info[1]}")
                        block_taskno += 2
                    else:
                        self.device_service.logger.error(f"{good_move_info[1]}")
                        return [False, f"{good_move_info[1]}"]
            else:
                self.device_service.logger.info("[SYSTEM] 无阻塞节点返回原位，无需处理")
            
            
            # ---------------------------------------- #
            # step 6: 数据库更新信息
            # ---------------------------------------- #

            self.device_service.logger.info(f"[step 6] 数据库更新信息")
            
            return_list = []
            
            sql_info_start = self.delete_pallet_by_loc(db, START_LOCATION)
            if sql_info_start:
                sql_start_returen = {
                    "id": sql_info_start.id,
                    "location": sql_info_start.location,
                    "pallet_id": sql_info_start.pallet_id,
                    "satus": sql_info_start.status
                }
                return_list.append(sql_start_returen)
            else:
                return [False, f"❌ 更新托盘号到({START_LOCATION})失败"]
            
            sql_info_end = self.update_pallet_by_loc(db, END_LOCATION, PALLET_ID)
            if sql_info_end:
                sql_end_returen = {
                    "id": sql_info_end.id,
                    "location": sql_info_end.location,
                    "pallet_id": sql_info_end.pallet_id,
                    "satus": sql_info_end.status
                }
                return_list.append(sql_end_returen)
                return [True, return_list]
            else:
                return [False, f"❌ 更新托盘号到({END_LOCATION})失败"]

        finally:
            self.release_lock()