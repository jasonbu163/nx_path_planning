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
            task_no = randint(1, 255)
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
            
            task_no = randint(1, 250)
            lift_move_info = await self.device_service.action_lift_move(task_no, target_layer)
            if lift_move_info[0]:
                self.plc_service.logger.info(f"{lift_move_info[1]}")
                lift_layer_info = await self.device_service.get_lift_layer()
                if lift_layer_info[0] and lift_layer_info[1] == 1:
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
            
            task_no = randint(1, 250)
            lift_move_info = await self.device_service.action_lift_move(task_no, target_layer)
            if lift_move_info[0]:
                self.plc_service.logger.info(f"{lift_move_info[1]}")
                lift_layer_info = await self.device_service.get_lift_layer()
                if lift_layer_info[0] and lift_layer_info[1] == 1:
                    self.plc_service.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
                else:
                    self.plc_service.logger.error(f"{lift_layer_info[1]}")
                    # return [False, f"{lift_layer_info[1]}"]
                    return False
            else:
                self.plc_service.logger.error(f"{lift_move_info[1]}")
                # return [False, f"{lift_move_info[1]}"]
                return False

            task_no = randint(1, 255)
            return await self.car_service.good_move(task_no+1, TARGET_LOCATION)
        
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
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

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

        finally:
            self.release_lock()


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
        

    async def do_task_inband_with_solve_blocking(
        self,
        TASK_NO: int,
        TARGET_LOCATION: str
        ) -> list:
        """
        [入库服务] - 操作穿梭车联动PLC系统入库, 使用障碍检测功能
        """

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
            target_loc = list(map(int, TARGET_LOCATION.split(',')))
            target_layer = target_loc[2]

            # 先让穿梭车跨层
            car_last_location = await self.device_service.car_cross_layer(
                TASK_NO,
                target_layer
                )
            
            # 获取当前层所有库位信息

            # 处理遮挡货物

            # 开始入库
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
        
        

    async def do_task_outband_with_solve_blocking(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
        """
        [出库服务] - 操作穿梭车联动PLC系统出库, 使用障碍检测功能
        """

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
            target_loc = list(map(int, TARGET_LOCATION.split(',')))
            target_layer = target_loc[2]

            # 先让穿梭车跨层
            car_last_location = await self.device_service.car_cross_layer(
                TASK_NO,
                target_layer
                )
            
            # 获取当前层所有库位信息

            # 处理遮挡货物

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
        