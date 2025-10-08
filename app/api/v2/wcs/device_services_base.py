# app/api/v2/wcs/device_services_base.py

from datetime import datetime
from typing import Optional, List, Tuple, Union, Dict, Any
from random import randint
import time
import asyncio
import json
# from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.base_model import TaskList as TaskModel
from app.models.base_model import LocationList as LocationModel
from app.models.base_enum import LocationStatus
from . import schemas
from app.utils.devices_logger import DevicesLogger

from app.map_core import PathCustom
# from app.devices.service_asyncio import DevicesService, DB_12
from app.devices import DevicesController, AsyncDevicesController, DevicesControllerByStep
from app.res_system.controller import AsyncSocketCarController
from app.res_system.controller import ControllerBase as CarController
from app.plc_system.controller import PLCController
from app.plc_system.enum import (
    DB_12,
    DB_11,
    FLOOR_CODE,
    LIFT_TASK_TYPE
)
from app.core.config import settings
from .services import LocationServices

class DeviceServicesBase(DevicesLogger):
    """设备服务, 同步通讯版"""

    def __init__(self):
        super().__init__(self.__class__.__name__)
        # self.thread_pool = thread_pool
        self._loop = None # 延迟初始化的事件循环引用
        self.path_planner = PathCustom()
        self.location_service = LocationServices()
        self.plc = PLCController(settings.PLC_IP)
        self.car = CarController(settings.CAR_IP, settings.CAR_PORT)
        self.device_service = DevicesController(settings.PLC_IP, settings.CAR_IP, settings.CAR_PORT)

        # 设备操作锁
        self.operation_lock = asyncio.Lock()
        self.operation_in_progress = False

    #################################################
    # 电梯锁服务
    #################################################

    async def acquire_lock(self):
        """获取电梯操作锁。"""
        # 检查锁是否已经被占用
        if self.operation_in_progress:
            return False
            
        acquired = await self.operation_lock.acquire()
        if acquired:
            self.operation_in_progress = True
            return True
        return False

    def release_lock(self):
        """释放电梯操作锁。"""
        self.operation_in_progress = False
        if self.operation_lock.locked():
            self.operation_lock.release()

    def is_operation_in_progress(self):
        """检查是否有电梯操作正在进行。"""
        return self.operation_in_progress
    
    #################################################
    # 穿梭车服务
    #################################################

    def get_car_current_location(self) -> Tuple[bool, str]:
        """获取穿梭车当前位置信息。"""
        msg = self.car.car_current_location()
        if msg == "error":
            return False, "操作失败，穿梭车可能未连接"
        return True, msg

    async def change_car_location_by_target(self, target: str) -> Tuple[bool, str]:
        """改变穿梭车位置。"""
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            task_no = randint(1, 100)
            car_info = self.car.change_car_location(task_no, target)
            if car_info:
                return True, f"操作成功，当前位置：{target}"
            else:
                return False, "操作失败"
        finally:
            self.release_lock()

    async def car_move_by_target(self, target_location: str) -> Tuple[bool, str]:
        """移动穿梭车。

        Args:
          target_location : 目标位置
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")
        
        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False, "❌ PLC连接错误"

            car_location = self.car.car_current_location()
            if car_location == "error":
                self.logger.error("❌ 获取穿梭车位置错误")
                return False, "❌ 获取穿梭车位置错误"
            else:
                self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
            
            car_loc = list(map(int, car_location.split(',')))
            car_layer = car_loc[2]

            target_loc = list(map(int, target_location.split(',')))
            target_layer = target_loc[2]

            if car_layer != target_layer:
                self.logger.error(f"❌ 操作失败，穿梭车层({car_layer})和任务层({target_layer})不一致")
                return False, f"❌ 操作失败，穿梭车层({car_layer})和任务层({target_layer})不一致"
            else:
                self.logger.info(f"✅ 穿梭车层({car_layer})和任务层({target_layer})一致")

            if car_location == target_location:
                self.logger.info(f"✅ 穿梭车已移动到目标位置({target_location})")
                return True, f"✅ 穿梭车已移动到目标位置({target_location})"
            else:
                self.logger.info(f"⌛️ 穿梭车开始移动...")
            
            task_no = randint(1, 100)

            if self.plc.plc_checker():

                last_task_no = self.plc.get_lift_last_taskno()
                if last_task_no == task_no:
                    task_no += 1
                    self.logger.info(f"🚧 获取任务号: {task_no}")
                else:
                    self.logger.info(f"🚧 获取任务号: {task_no}")

                if self.plc.lift_move_by_layer_sync(task_no, car_layer):
                    self.logger.info("✅ 电梯工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 电梯工作指令发送失败")
                    return False ,"❌ 电梯工作指令发送失败"
                
                self.logger.info(f"⌛️ 等待电梯到达{car_layer}层")

                if self.plc.wait_lift_move_complete_by_location_sync():
                    self.logger.info(f"✅ 电梯已到达{car_layer}层")
                else:
                    self.plc.disconnect()
                    self.logger.error(f"❌ 电梯未到达{car_layer}层")
                    return False, f"❌ 电梯未到达{car_layer}层"
                
                if self.car.car_move(task_no+1, target_location):
                    self.logger.info("✅ 穿梭车移动指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 穿梭车移动指令发送错误")
                    return False, "❌ 穿梭车移动指令发送错误"
                
                if self.car.wait_car_move_complete_by_location_sync(target_location):
                    self.logger.info(f"✅ 穿梭车已到达 {target_location} 位置")
                else:
                    self.plc.disconnect()
                    self.logger.error(f"❌ 穿梭车未到达 {target_location} 位置")
                    return False, f"❌ 穿梭车未到达 {target_location} 位置"
            
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False, "❌ PLC错误"
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False, "❌ PLC断开连接错误"
            
            self.logger.info(f"✅ 任务完成")
            return True, f"✅ 任务完成"

        finally:
            self.release_lock()

    async def good_move_by_target(self, target_location: str) -> Tuple[bool, str]:
        """移动货物服务。

        Args:
          target_location: 目标位置
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")
        
        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False, "❌ PLC连接错误"

            car_location = self.car.car_current_location()
            if car_location == "error":
                self.logger.error("❌ 获取穿梭车位置错误")
                return False, "❌ 获取穿梭车位置错误"
            else:
                self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
            
            car_loc = list(map(int, car_location.split(',')))
            car_layer = car_loc[2]

            target_loc = list(map(int, target_location.split(',')))
            target_layer = target_loc[2]

            if car_layer != target_layer:
                self.logger.error(f"❌ 操作失败，穿梭车层({car_layer})和任务层({target_layer})不一致")
                return False, f"❌ 操作失败，穿梭车层({car_layer})和任务层({target_layer})不一致"
            else:
                self.logger.info(f"✅ 穿梭车层({car_layer})和任务层({target_layer})一致")

            if car_location == target_location:
                self.logger.info(f"✅ 穿梭车已移动到目标位置({target_location})")
                return True, f"✅ 穿梭车已移动到目标位置({target_location})"
            else:
                self.logger.info(f"⌛️ 穿梭车开始移动...")
            
            task_no = randint(1, 100)

            if self.plc.plc_checker():

                last_task_no = self.plc.get_lift_last_taskno()
                if last_task_no == task_no:
                    task_no += 1
                    self.logger.info(f"🚧 获取任务号: {task_no}")
                else:
                    self.logger.info(f"🚧 获取任务号: {task_no}")

                if self.plc.lift_move_by_layer_sync(task_no, car_layer):
                    self.logger.info("✅ 电梯工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 电梯工作指令发送失败")
                    return False ,"❌ 电梯工作指令发送失败"
                
                self.logger.info(f"⌛️ 等待电梯到达{car_layer}层")

                if self.plc.wait_lift_move_complete_by_location_sync():
                    self.logger.info(f"✅ 电梯已到达{car_layer}层")
                else:
                    self.plc.disconnect()
                    self.logger.error(f"❌ 电梯未到达{car_layer}层")
                    return False, f"❌ 电梯未到达{car_layer}层"

                if self.car.good_move(task_no+1, target_location):
                    self.logger.info("✅ 穿梭车移动指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 穿梭车移动指令发送错误")
                    return False, "❌ 穿梭车移动指令发送错误"
                
                if self.car.wait_car_move_complete_by_location_sync(target_location):
                    self.logger.info(f"✅ 穿梭车已到达 {target_location} 位置")
                else:
                    self.plc.disconnect()
                    self.logger.error(f"❌ 穿梭车未到达 {target_location} 位置")
                    return False, f"❌ 穿梭车未到达 {target_location} 位置"
            
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False, "❌ PLC错误"
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False, "❌ PLC断开连接错误"
            
            self.logger.info(f"✅ 任务完成")
            return True, f"✅ 任务完成"
        
        finally:
            self.release_lock()
    
    async def good_move_by_start_end(
            self, 
            start_location: str, 
            end_location: str
    ) -> Tuple[bool, str]:
        """移动货物。

        根据起点位置和终点位置，车辆自动前往目标位置，再执行货物移动。

        Args:
          start_location: 起点位置
          end_location: 终点位置
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")
        
        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False, "❌ PLC连接错误"

            car_location = self.car.car_current_location()
            if car_location == "error":
                self.logger.error("❌ 获取穿梭车位置错误")
                return False, "❌ 获取穿梭车位置错误"
            else:
                self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
            
            car_loc = list(map(int, car_location.split(',')))
            car_layer = car_loc[2]

            # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
            start_loc = list(map(int, start_location.split(',')))
            start_layer = start_loc[2]
            
            end_loc = list(map(int, end_location.split(',')))
            end_layer = end_loc[2]

            if start_layer != end_layer:
                return False, f"操作失败，起点{start_layer}和终点{end_layer}楼层不一致"
            
            if car_layer != start_layer or car_layer != end_layer:
                return False, f"操作失败，穿梭车层{car_layer}、起点{start_layer}、终点{end_layer}楼层必须保持一致"
            
            task_no = randint(1, 100)

            if self.plc.plc_checker():

                last_task_no = self.plc.get_lift_last_taskno()
                if last_task_no == task_no:
                    task_no += 1
                    self.logger.info(f"🚧 获取任务号: {task_no}")
                else:
                    self.logger.info(f"🚧 获取任务号: {task_no}")

                if self.plc.lift_move_by_layer_sync(task_no, car_layer):
                    self.logger.info("✅ 电梯工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 电梯工作指令发送失败")
                    return False ,"❌ 电梯工作指令发送失败"
                
                self.logger.info(f"⌛️ 等待电梯到达{car_layer}层")

                if self.plc.wait_lift_move_complete_by_location_sync():
                    self.logger.info(f"✅ 电梯已到达{car_layer}层")
                else:
                    self.plc.disconnect()
                    self.logger.error(f"❌ 电梯未到达{car_layer}层")
                    return False, f"❌ 电梯未到达{car_layer}层"
                
                if car_location == start_location:
                    self.logger.info(f"✅ 穿梭车已到达 {start_location} 位置")
                else:
                    self.logger.info(f"⌛️ 穿梭车开始移动...")

                    if self.car.car_move(task_no+1, start_location):
                        self.logger.info("✅ 穿梭车移动指令发送成功")
                    else:
                        self.plc.disconnect()
                        self.logger.error("❌ 穿梭车移动指令发送错误")
                        return False, "❌ 穿梭车移动指令发送错误"
                    
                    if self.car.wait_car_move_complete_by_location_sync(start_location):
                        self.logger.info(f"✅ 穿梭车已到达 {start_location} 位置")
                    else:
                        self.plc.disconnect()
                        self.logger.error(f"❌ 穿梭车未到达 {start_location} 位置")
                        return False, f"❌ 穿梭车未到达 {start_location} 位置"

                if self.car.good_move(task_no+2, end_location):
                    self.logger.info("✅ 穿梭车移动指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 穿梭车移动指令发送错误")
                    return False, "❌ 穿梭车移动指令发送错误"
                
                if self.car.wait_car_move_complete_by_location_sync(end_location):
                    self.logger.info(f"✅ 穿梭车已到达 {end_location} 位置")
                else:
                    self.plc.disconnect()
                    self.logger.error(f"❌ 穿梭车未到达 {end_location} 位置")
                    return False, f"❌ 穿梭车未到达 {end_location} 位置"
                
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False, "❌ PLC错误"
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False, "❌ PLC断开连接错误"
            
            self.logger.info(f"✅ 任务完成")
            return True, f"✅ 任务完成"
        
        finally:
            self.release_lock()

    async def good_move_by_start_end_no_lock(
            self,
            task_no: int,
            start_location: str, 
            end_location: str
    ) -> Tuple[bool, str]:
        """移动货物。

        根据起点位置和终点位置，车辆自动前往目标位置，再执行货物移动。

        Args:
          start_location: 起点位置
          end_location: 终点位置
        """

        car_location = self.car.car_current_location()
        if car_location == "error":
            self.logger.error("❌ 获取穿梭车位置错误")
            return False, "❌ 获取穿梭车位置错误"
        else:
            self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
            
        car_loc = list(map(int, car_location.split(',')))
        car_layer = car_loc[2]

        # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        start_loc = list(map(int, start_location.split(',')))
        start_layer = start_loc[2]
        
        end_loc = list(map(int, end_location.split(',')))
        end_layer = end_loc[2]

        if task_no >= 250:
            task_no = 50

        if start_layer != end_layer:
            return False, f"操作失败，起点{start_layer}和终点{end_layer}楼层不一致"
        
        if car_layer != start_layer or car_layer != end_layer:
            return False, f"操作失败，穿梭车层{car_layer}、起点{start_layer}、终点{end_layer}楼层必须保持一致"
                
        if car_location == start_location:
            self.logger.info(f"✅ 穿梭车已到达 {start_location} 位置")
        else:
            self.logger.info(f"⌛️ 穿梭车开始移动...")

            if self.car.car_move(task_no+21, start_location):
                self.logger.info("✅ 穿梭车移动指令发送成功")
            else:
                self.logger.error("❌ 穿梭车移动指令发送错误")
                return False, "❌ 穿梭车移动指令发送错误"
                        
            if self.car.wait_car_move_complete_by_location_sync(start_location):
                self.logger.info(f"✅ 穿梭车已到达 {start_location} 位置")
            else:
                self.logger.error(f"❌ 穿梭车未到达 {start_location} 位置")
                return False, f"❌ 穿梭车未到达 {start_location} 位置"

        if self.car.good_move(task_no+22, end_location):
            self.logger.info("✅ 穿梭车移动指令发送成功")
        else:
            self.logger.error("❌ 穿梭车移动指令发送错误")
            return False, "❌ 穿梭车移动指令发送错误"
                
        if self.car.wait_car_move_complete_by_location_sync(end_location):
            self.logger.info(f"✅ 穿梭车已到达 {end_location} 位置")
        else:
            self.logger.error(f"❌ 穿梭车未到达 {end_location} 位置")
            return False, f"❌ 穿梭车未到达 {end_location} 位置"
            
        self.logger.info(f"✅ 任务完成")
        return True, f"✅ 任务完成"

    #################################################
    # 电梯服务
    #################################################
        
    async def lift_by_id(
            self,
            layer: int
    ) -> Tuple[bool, str]:
        """控制提升机。"""
        # 尝试获取电梯操作锁
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False, "❌ PLC连接错误"
            
            task_no = randint(1, 100)

            if self.plc.plc_checker():

                last_task_no = self.plc.get_lift_last_taskno()
                if last_task_no == task_no:
                    task_no += 1
                    self.logger.info(f"🚧 获取任务号: {task_no}")
                else:
                    self.logger.info(f"🚧 获取任务号: {task_no}")

                if self.plc.lift_move_by_layer_sync(task_no, layer):
                    self.logger.info("✅ 电梯工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 电梯工作指令发送失败")
                    return False ,"❌ 电梯工作指令发送失败"
                
                self.logger.info(f"⌛️ 等待电梯到达{layer}层")

                if self.plc.wait_lift_move_complete_by_location_sync():
                    self.logger.info(f"✅ 电梯已到达{layer}层")
                else:
                    self.plc.disconnect()
                    self.logger.error(f"❌ 电梯未到达{layer}层")
                    return False, f"❌ 电梯未到达{layer}层"
            
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False, "❌ PLC错误"
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False, "❌ PLC断开连接错误"
            
            self.logger.info(f"✅ 任务完成")
            return True, f"✅ 任务完成"
        
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
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False
            
            if self.plc.plc_checker():

                self.plc.logger.info("📦 货物开始进入电梯...")
                
                if self.plc.inband_to_lift():
                    self.logger.info("✅ PLC工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ PLC工作指令发送失败")
                    return False

                self.plc.logger.info("⏳ 输送线移动中...")

                if self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1):
                    self.logger.info("✅ 货物到达电梯")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 输送线未移动完成")
                    return False
            
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False
            
            self.logger.info(f"✅ 任务完成")
            return True
        
        finally:
            self.release_lock()


    async def task_lift_outband(self) -> bool:
        """
        [货物 - 出库方向] 电梯 -> 出口
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False

            if self.plc.plc_checker():

                self.plc.logger.info("📦 货物开始离开电梯...")

                if self.plc.lift_to_outband():
                    self.logger.info("✅ PLC指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ PLC指令发送错误")
                    return False

                self.plc.logger.info("⏳ 输送线移动中...")

                if self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1):
                    self.logger.info("✅ 货物到达出口")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 货物离开电梯出库失败")
                    return False
                
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False
            
            self.logger.info(f"✅ 任务完成")
            return True

        finally:
            self.release_lock()

    async def feed_in_progress(self, target_layer: int) -> bool:
        """
        [货物 - 出库方向] 货物进入电梯
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False
            
            if self.plc.plc_checker():
                
                self.plc.logger.info(f"📦 开始移动 {target_layer}层 货物到电梯前")
                
                if self.plc.feed_in_process(target_layer):
                    self.logger.info("✅ PLC工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ PLC工作指令发送失败")
                    return False
            
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False
            
            self.logger.info(f"✅ 任务完成")
            return True
            
        finally:
            self.release_lock()

    async def feed_complete(self, target_layer: int) -> bool:
        """
        [货物 - 出库方向] 库内放货完成信号

        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False

            if self.plc.plc_checker():
                
                self.plc.logger.info(f"✅ 货物放置完成")
                
                if self.plc.feed_complete(target_layer):
                    self.logger.info("✅ PLC工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ PLC工作指令发送失败")
                    return False

                self.plc.logger.info("⏳ 输送线移动中...")

                if self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1):
                    self.logger.info("✅ 货物到达电梯")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 货物进入电梯失败")
                    return False
            
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False
            
            self.logger.info(f"✅ 任务完成")
            return True

        finally:
            self.release_lock()
        

    async def out_lift(self, target_layer:int) -> bool:
        """
        [货物 - 入库方向] 货物离开电梯, 进入库内接驳位 (最后附带取货进行中信号发送)
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False

            if self.plc.plc_checker():
            
                # 确认电梯到位后，清除到位状态
                self.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                if self.plc.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.plc.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ PLC运行错误")
                    return False
                
                await asyncio.sleep(1)
                self.plc.logger.info("📦 货物开始进入楼层...")
                self.plc.lift_to_everylayer(target_layer)
                    
                self.plc.logger.info("⏳ 等待输送线动作完成...")
                # 等待电梯输送线工作结束
                if target_layer == 1:
                    if self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1030.value, 1):
                        self.logger.info(f"✅ 货物到达 {target_layer} 层接驳位")
                    else:
                        self.plc.disconnect()
                        self.logger.error("❌ 输送线未移动完成")
                        return False
                    
                elif target_layer == 2:
                    if self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1040.value, 1):
                        self.logger.info(f"✅ 货物到达 {target_layer} 层接驳位")
                    else:
                        self.plc.disconnect()
                        self.logger.error("❌ 输送线未移动完成")
                        return False
                
                elif target_layer == 3:
                    if self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1050.value, 1):
                        self.logger.info(f"✅ 货物到达 {target_layer} 层接驳位")
                    else:
                        self.plc.disconnect()
                        self.logger.error("❌ 输送线未移动完成")
                        return False
                
                elif target_layer == 4:
                    if self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1060.value, 1):
                        self.logger.info(f"✅ 货物到达 {target_layer} 层接驳位")
                    else:
                        self.plc.disconnect()
                        self.logger.error("❌ 输送线未移动完成")
                        return False
                
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ 目标楼层错误")
                    return False
                
                self.plc.logger.info("⌛️ 可以开始取货...")

                if self.plc.pick_in_process(target_layer):
                    self.logger.info("✅ PLC工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ PLC工作指令发送失败")
                    return False
                
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接失败")
                return False
            
            self.logger.info("🚧 断开PLC连接")
        
            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False
            
            self.logger.info(f"✅ 任务完成")
            return True

        finally:
            self.release_lock()
        
    async def pick_complete(self, target_layer:int) -> bool:
        """
        [货物 - 入库方向] 库内取货完成信号
        """
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            self.logger.info("🚧 连接PLC")
        
            if self.plc.connect():
                self.logger.info("✅ PLC连接正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC连接错误")
                return False
            
            if self.plc.plc_checker():
                
                self.logger.info(f"✅ 货物取货完成")

                if self.plc.pick_complete(target_layer):
                    self.logger.info("✅ PLC工作指令发送成功")
                else:
                    self.plc.disconnect()
                    self.logger.error("❌ PLC工作指令发送失败")
                    return False
            
            else:
                self.plc.disconnect()
                self.logger.error("❌ PLC错误")
                return False
            
            self.logger.info("🚧 断开PLC连接")

            if self.plc.disconnect():
                self.logger.info("✅ PLC已断开")
            else:
                self.logger.error("❌ PLC断开连接错误")
                return False
            
            self.logger.info(f"✅ 任务完成")
            return True

        finally:
            self.release_lock()

    #################################################
    # 出入口二维码服务
    #################################################

    async def get_qrcode(self) -> Union[bytes, bool]:
        """获取入库口二维码"""

        self.logger.info("🚧 连接PLC")
        
        if self.plc.connect():
            self.logger.info("✅ PLC连接正常")
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC连接错误")
            return False
        
        if self.plc.plc_checker():

            QRcode = self.plc.scan_qrcode()
            if QRcode == False:
                self.plc.disconnect()
                return False
            else:
                self.logger.info(f"✅ 获取托盘号为：{QRcode}")

        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return False
            
        self.logger.info("🚧 断开PLC连接")

        if self.plc.disconnect():
            self.logger.info("✅ PLC已断开")
        else:
            self.logger.error("❌ PLC断开连接错误")
            return False
            
        self.logger.info(f"✅ 任务完成")
        return QRcode


    #################################################
    # 设备联动服务
    #################################################

    async def do_car_cross_layer(
            self,
            task_no: int,
            target_layer: int
    ) -> Tuple[bool, str]:
        """[穿梭车跨层] 操作穿梭车联动电梯跨层。"""

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            start = time.time()

            msg = self.device_service.car_cross_layer(task_no, target_layer)

            elapsed = time.time() - start
            self.logger.info(f"程序用时: {elapsed:.6f}s")
            
            return msg

        finally:
            self.release_lock()

        
    async def do_task_inband(
            self,
            task_no: int,
            target_location: str
    ) -> Tuple[bool, str]:
        """[入库服务] 操作穿梭车联动PLC系统入库(无障碍检测)。"""
        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            start = time.time()

            msg = self.device_service.task_inband(task_no, target_location)

            elapsed = time.time() - start
            self.logger.info(f"程序用时: {elapsed:.6f}s")
            
            return msg

        finally:
            self.release_lock()
    
    async def do_task_outband(
            self,
            task_no: int,
            target_location: str
    ) -> Tuple[bool, str]:
        """[出库服务] 操作穿梭车联动PLC系统出库(无障碍检测)。"""

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            start = time.time()

            msg = self.device_service.task_outband(task_no, target_location)

            elapsed = time.time() - start
            self.logger.info(f"程序用时: {elapsed:.6f}s")
            
            return msg

        finally:
            self.release_lock()
        
    def get_block_node(
        self,
        start_location: str,
        end_location: str,
        db: Session
    ) -> Tuple[bool, Union[str, List]]:
        """[获取阻塞节点] 用于获取阻塞节点。

        Args:
            start_location: 路径起点
            end_location: 路径终点
            db: Session 数据库会话

        Resturns:
            Tuple: [bool, 阻塞节点列表]
        """
        
        # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        start_loc = list(map(int, start_location.split(',')))
        start_layer = start_loc[2]
        end_loc = list(map(int, end_location.split(',')))
        end_layer = end_loc[2]

        if start_layer != end_layer:
            return False, "❌ 起点与终点楼层不一致"
        
        # 获取当前层所有库位信息
        node_status = dict()
        if start_layer == 1:
            success, location_info = self.location_service.get_location_by_start_to_end(db=db, start_id=124, end_id=164)
            if success:
                all_nodes = location_info
            else:
                return False, f"{location_info}"
        elif start_layer == 2:
            success, location_info = self.location_service.get_location_by_start_to_end(db=db, start_id=83, end_id=123)
            if success:
                all_nodes = location_info
            else:
                return False, f"{location_info}"
        elif start_layer == 3:
            success, location_info = self.location_service.get_location_by_start_to_end(db=db, start_id=42, end_id=82)
            if success:
                all_nodes = location_info
            else:
                return False, f"{location_info}"
        elif start_layer == 4:
            success, location_info = self.location_service.get_location_by_start_to_end(db=db, start_id=1, end_id=41)
            if success:
                all_nodes = location_info
            else:
                return False, f"{location_info}"
        else:
            self.logger.error("❌ 未找到符合条件的库位信息")
            return False, "❌ 未找到符合条件的库位信息"
            
        # 检查all_locations是否为列表
        if isinstance(all_nodes, list):
            # 打印每个位置的详细信息
            for node in all_nodes:
                # print(f"ID: {location.id}, 托盘号: {location.pallet_id}, 坐标: {location.location}, 状态: {location.status}")                        
                # node_status[node.location] = [node.id, node.status, node.pallet_id]
                if node.status in ["lift", "highway"]:
                    continue
                node_status[node.location] = node.status
                
            print(f"[SYSTEM] 第 {start_layer} 层有 {len(node_status)} 个节点")
            # return [True, node_status]
            
            blocking_nodes = self.path_planner.find_blocking_nodes(start_location, end_location, node_status)
        
            return True, blocking_nodes
                
        else:
            self.logger.error("❌ 库位信息获取失败")
            return False, "❌ 库位信息获取失败"
            
    async def do_task_inband_with_solve_blocking(
            self,
            task_no: int,
            target_location: str,
            new_pallet_id: str,
            db: Session
    ) -> Tuple[bool, Union[Dict,str]]:
        """[入库服务 - 数据库] 操作穿梭车联动PLC系统入库, 使用障碍检测功能。"""

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            self.logger.info(f"[入库服务 - 数据库] - 操作穿梭车联动PLC系统入库, 使用障碍检测功能")
            
            # ---------------------------------------- #
            # base 1: 获取入库口托盘信息，并校验托盘信息
            # ---------------------------------------- #

            self.logger.info(f"[base 1] 获取入库口托盘信息，并校验托盘信息")

            success, sql_qrcode_info = self.location_service.get_location_by_pallet_id(db, new_pallet_id)
            if not success:
                self.logger.info(f"[订单托盘号校验] - ✅ 订单托盘不在库内，可以入库")
            else:
                self.logger.info(f"[订单托盘号校验] - ❌ 订单托盘已在库内，禁止入库")
                return False, "❌ 订单托盘已在库内"
            
            # 获取入库口托盘信息
            qrcode_info = await self.get_qrcode()
            if not qrcode_info:
                return False, "❌ 获取二维码信息失败"
            
            # 统一转换为字符串处理
            if isinstance(qrcode_info, bytes):
                try:
                    inband_qrcode_info = qrcode_info.decode('utf-8')
                except UnicodeDecodeError:
                    return False, "❌ 二维码解码失败"
            elif isinstance(qrcode_info, str):
                inband_qrcode_info = qrcode_info
            else:
                return False, "❌ 二维码信息格式无效"
            
            if new_pallet_id != inband_qrcode_info:
                return False, "❌ 订单托盘号和入库口托盘号不一致"
            self.logger.info(f"[入口托盘号校验] - ✅ 入口托盘号与订单托盘号一致: {inband_qrcode_info}")
            
            # ---------------------------------------- #
            # base 2: 校验订单目标位置
            # ---------------------------------------- #

            self.logger.info(f"[base 2] 校验订单目标位置")

            buffer_list = {
                "1,3,1", "2,3,1", "3,3,1", "5,3,1", "6,3,1",
                "1,3,2", "2,3,2", "3,3,2", "5,3,2", "6,3,2",
                "1,3,3", "2,3,3", "3,3,3", "5,3,3", "6,3,3",
                "1,3,4", "2,3,4", "3,3,4", "5,3,4", "6,3,4"
                }
            # buffer_list = {"5,3,1", "5,3,2", "5,3,3", "5,3,4"}

            if target_location in buffer_list:
                return False, f"❌ {target_location} 位置为接驳位，不能直接使用此功能操作"
            
            success, location_info = self.location_service.get_location_by_loc(db, target_location)
            if not success:
                return False, f"{location_info}"
            else:
                if isinstance(location_info, List):
                    if location_info.status in ["occupied", "lift", "highway"]:
                        return False, f"❌ 入库目标错误，目标状态为{location_info.status}"
                    else:
                        self.logger.info(f"[入库位置校验] ✅ 入库位置状态 - {location_info.status}")
                        self.logger.info(f"[SYSTEM] 入库位置信息 - id:{location_info.id}, 位置:{location_info.location}, 托盘号:{location_info.pallet_id}, 状态:{location_info.status}")
                else:
                    return False, f"获取到未知的成功响应类型: {type(location_info)}"

            # ---------------------------------------- #
            # step 1: 解析目标库位信息
            # ---------------------------------------- #

            self.logger.info("[step 1] 解析目标库位信息")
            
            target_loc = list(map(int, target_location.split(',')))
            target_layer = target_loc[2]
            inband_location = f"5,3,{target_layer}"

            # ---------------------------------------- #
            # step 2: 判断是否需要穿梭车跨层
            # ---------------------------------------- #

            self.logger.info("[step 2] 判断是否需要穿梭车跨层")
            
            success, car_move_info = self.device_service.car_cross_layer(task_no, target_layer)
            if success:
                self.logger.info(f"{car_move_info}")
            else:
                self.logger.error(f"{car_move_info}")
                return False, f"{car_move_info}"
            
            # ---------------------------------------- #
            # step 3: 处理入库阻挡货物
            # ---------------------------------------- #

            self.logger.info("[step 3] 处理入库阻挡货物")

            success, blocking_nodes = self.get_block_node(inband_location, target_location, db)
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
                        
                self.logger.info(f"[SYSTEM] 靠近高速道阻塞点(按距离排序): {do_blocking_nodes}")

                # 定义临时存放点
                temp_storage_nodes = [f"1,3,{target_layer}", f"2,3,{target_layer}", f"3,3,{target_layer}"]
                # 记录移动映射关系，用于将货物移回原位
                move_mapping = {}

                # step 3.2: 处理遮挡货物
                block_taskno = task_no+1
                for i, blocking_node in enumerate(do_blocking_nodes):
                    if i < len(temp_storage_nodes):
                        temp_node = temp_storage_nodes[i]
                        self.logger.info(f"[CAR] 移动({blocking_node})遮挡货物到({temp_node})")
                        move_mapping[blocking_node] = temp_node

                        # 移动货物
                        success, good_move_info = await self.good_move_by_start_end_no_lock(block_taskno, blocking_node, temp_node)
                        if success:
                            self.logger.info(f"{good_move_info}")
                            block_taskno += 3
                        else:
                            self.logger.error(f"{good_move_info}")
                            return False, f"{good_move_info}"

                    else:
                        self.logger.warning(f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})")
                        return False, f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})"
            else:
                self.logger.info("[SYSTEM] 无阻塞节点，直接出库")

            # ---------------------------------------- #
            # step 4: 货物入库
            # ---------------------------------------- #

            self.logger.info(f"[step 4] 货物入库至位置({target_location})")
            
            success, good_move_info = self.device_service.task_inband(task_no+2, target_location)
            if success:
                self.logger.info(f"货物入库至({target_location})成功")
            else:
                self.logger.error(f"货物出库至({target_location})失败")
                return False, f"货物出库至({target_location})失败"
            
            # ---------------------------------------- #
            # step 5: 移动遮挡货物返回到原位（按相反顺序）
            # ---------------------------------------- #

            self.logger.info(f"[step 5] 移动遮挡货物返回到原位（按相反顺序）")
            
            block_taskno = task_no+3
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                for blocking_node, temp_node in reversed(list(move_mapping.items())):
                    self.logger.info(f"[CAR] 移动({temp_node})遮挡货物返回({blocking_node})")
                    
                    # 移动货物
                    success, good_move_info = await self.good_move_by_start_end_no_lock(block_taskno, temp_node, blocking_node)
                    if success:
                        self.logger.info(f"{good_move_info}")
                        block_taskno += 3
                    else:
                        self.logger.error(f"{good_move_info}")
                        return False, f"{good_move_info}"
            else:
                self.logger.info("[SYSTEM] 无阻塞节点返回原位，无需处理")
            
            # ---------------------------------------- #
            # step 6: 数据库更新信息
            # ---------------------------------------- #

            self.logger.info(f"[step 6] 数据库更新信息")
            
            update_pallet_id = inband_qrcode_info # 生产用
            # update_pallet_id = new_pallet_id # 测试用
            
            success, sql_info = self.location_service.update_pallet_by_loc(db, target_location, update_pallet_id)
            if not success:
                self.logger.error(f"[SYSTEM] ❌ {sql_info}")
                return False, f"{sql_info}"
            else:
                if isinstance(sql_info, List):
                    sql_returen = {
                        "id": sql_info.id,
                        "location": sql_info.location,
                        "pallet_id": sql_info.pallet_id,
                        "satus": sql_info.status
                    }
                    return True, sql_returen
                else:
                    return False, f"获取到未知的成功响应类型: {type(location_info)}"

        finally:
            self.release_lock()
        
    async def do_task_outband_with_solve_blocking(
            self,
            task_no: int,
            target_location: str,
            new_pallet_id: str,
            db: Session
    ) -> Tuple[bool, Union[Dict, str]]:
        """[出库服务 - 数据库] - 操作穿梭车联动PLC系统出库, 使用障碍检测功能"""

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:

            self.logger.info(f"[出库服务 - 数据库] - 操作穿梭车联动PLC系统出库, 使用障碍检测功能")
            
            # ---------------------------------------- #
            # base 1: 解析订单托盘信息，并且校验托盘信息
            # ---------------------------------------- #

            self.logger.info(f"[base 1] 解析订单托盘信息，并且校验托盘信息")

            success, sql_qrcode_info = self.location_service.get_location_by_pallet_id(db, new_pallet_id)

            if not success:
                self.logger.error(f"[订单托盘校验] - ❌ 订单托盘不在库内")
                return False, f"❌ {sql_qrcode_info}"
            else:
                if isinstance(sql_qrcode_info, LocationModel):
                    
                    self.logger.info(f"[订单托盘校验] - ✅ 订单托盘在库内")
              
                    if sql_qrcode_info.location in [target_location]:
                        self.logger.info(f"[订单托盘校验] - ✅ 订单托盘位置与库位匹配")
                    else:
                        self.logger.error(f"[订单托盘校验] - ❌ 订单托盘位置与库位不匹配")
                        return False, "❌ 订单托盘位置与库位不匹配"
                
                else:
                    return False, f"获取到未知的成功响应类型: {type(sql_qrcode_info)}"
            
            # ---------------------------------------- #
            # base 2: 校验订单目标位置
            # ---------------------------------------- #

            self.logger.info(f"[base 2] 校验订单目标位置")

            buffer_list = {
                "1,3,1", "2,3,1", "3,3,1", "5,3,1",
                "1,3,2", "2,3,2", "3,3,2", "5,3,2",
                "1,3,3", "2,3,3", "3,3,3", "5,3,3",
                "1,3,4", "2,3,4", "3,3,4", "5,3,4"
                }
            
            if target_location in buffer_list:
                self.logger.error(f"[出库位置校验] ❌ {target_location} 位置为接驳位/缓冲位，不能使用此功能操作")
                return False, f"❌ {target_location} 位置为接驳位/缓冲位，不能使用此功能操作"
            
            success, location_info = self.location_service.get_location_by_loc(db, target_location)
            if not success:
                return False, f"{location_info}"
            else:
                if isinstance(location_info, List):
                    if location_info.status in ["free", "lift", "highway"]:
                        return False, f"❌ 出库目标错误，目标状态为{location_info.status}"
                    else:
                        self.logger.info(f"[出库位置校验] ✅ 出库位置状态 - {location_info.status}")
                        self.logger.info(f"[SYSTEM] 出库位置信息 - id:{location_info.id}, 位置:{location_info.location}, 托盘号:{location_info.pallet_id}, 状态:{location_info.status}")
                else:
                    return False, f"获取到未知的成功响应类型: {type(location_info)}"
            
            # ---------------------------------------- #
            # step 1: 解析目标库位信息
            # ---------------------------------------- #

            self.logger.info("[step 1] 获取目标库位信息")
            
            target_loc = list(map(int, target_location.split(',')))
            target_layer = target_loc[2]
            outband_location = f"5,3,{target_layer}"
            
            # ---------------------------------------- #
            # step 2: 判断是否需要穿梭车跨层
            # ---------------------------------------- #

            self.logger.info("[step 2] 先让穿梭车跨层")
            
            success, car_move_info = self.device_service.car_cross_layer(task_no, target_layer)
            if success:
                self.logger.info(f"{car_move_info}")
            else:
                self.logger.error(f"{car_move_info}")
                return False, f"{car_move_info}"
            
            # ---------------------------------------- #
            # step 3: 处理出库阻挡货物
            # ---------------------------------------- #

            self.logger.info("[step 3] 处理出库阻挡货物")

            blocking_nodes = self.get_block_node(target_location, outband_location, db)
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
                        
                self.logger.info(f"[SYSTEM] 靠近高速道阻塞点(按距离排序): {do_blocking_nodes}")

                # 定义临时存放点
                temp_storage_nodes = [f"1,3,{target_layer}", f"2,3,{target_layer}", f"3,3,{target_layer}"]
                # 记录移动映射关系，用于将货物移回原位
                move_mapping = {}

                # step 3.2: 处理遮挡货物
                block_taskno = task_no+1
                for i, blocking_node in enumerate(do_blocking_nodes):
                    if i < len(temp_storage_nodes):
                        temp_node = temp_storage_nodes[i]
                        self.logger.info(f"[CAR] 移动({blocking_node})遮挡货物到({temp_node})")
                        move_mapping[blocking_node] = temp_node

                        # 移动货物
                        success, good_move_info = await self.good_move_by_start_end_no_lock(block_taskno, blocking_node, temp_node)
                        if success:
                            self.logger.info(f"{good_move_info}")
                            block_taskno += 3
                        else:
                            self.logger.error(f"{good_move_info}")
                            return False, f"{good_move_info}"

                    else:
                        self.logger.warning(f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})")
                        return False, f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})"
            else:
                self.logger.info("[SYSTEM] 无阻塞节点，直接出库")

            # ---------------------------------------- #
            # step 4: 货物出库
            # ---------------------------------------- #

            self.logger.info(f"[step 4] ({target_location})货物出库")
           
            success, good_move_info = self.device_service.task_outband(task_no+2, target_location)
            if success:
                self.logger.info(f"{target_location}货物出库成功")
            else:
                self.logger.error(f"{target_location}货物出库失败")
                return False, f"{target_location}货物出库失败"

            # ---------------------------------------- #
            # step 5: 移动遮挡货物返回到原位（按相反顺序）
            # ---------------------------------------- #

            self.logger.info(f"[step 5] 移动遮挡货物返回到原位（按相反顺序）")
            
            block_taskno = task_no+3
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                for blocking_node, temp_node in reversed(list(move_mapping.items())):
                    self.logger.info(f"[CAR] 移动({temp_node})遮挡货物返回({blocking_node})")
                    
                    # 移动货物
                    success, good_move_info = await self.good_move_by_start_end_no_lock(block_taskno, temp_node, blocking_node)
                    if success:
                        self.logger.info(f"{good_move_info}")
                        block_taskno += 3
                    else:
                        self.logger.error(f"{good_move_info}")
                        return False, f"{good_move_info}"
            else:
                self.logger.info("[SYSTEM] 无阻塞节点返回原位，无需处理")
            
            # ---------------------------------------- #
            # step 6: 数据库更新信息
            # ---------------------------------------- #

            self.logger.info(f"[step 6] 数据库更新信息")
            
            success, sql_info = self.location_service.delete_pallet_by_loc(db, target_location)
            if not success:
                self.logger.error(f"❌ {sql_info}")
                return False, f"{sql_info}"
            else:
                if isinstance(sql_info, List):
                    sql_returen = {
                        "id": sql_info.id,
                        "location": sql_info.location,
                        "pallet_id": sql_info.pallet_id,
                        "satus": sql_info.status
                    }
                    return True, sql_returen
                else:
                    return False, f"获取到未知的成功响应类型: {type(location_info)}"

        finally:
            self.release_lock()
        
    async def do_good_move_with_solve_blocking(
            self,
            task_no: int,
            pallet_id: str, 
            start_location: str,
            end_location: str,
            db: Session
    ) -> Tuple[bool, Union[str, List]]:
        """[货物移动服务 - 数据库] 操作穿梭车联动PLC系统移动货物, 使用障碍检测功能。"""

        if not await self.acquire_lock():
            raise RuntimeError("正在执行其他操作，请稍后再试")

        try:
            self.logger.info(f"[货物移动服务 - 数据库] 操作穿梭车联动PLC系统移动货物, 使用障碍检测功能")
            
            # ---------------------------------------- #
            # base 1: 解析订单托盘信息，并且校验托盘信息
            # ---------------------------------------- #

            self.logger.info(f"[base 1] 解析订单托盘信息，并且校验托盘信息")

            success, sql_qrcode_info = self.location_service.get_location_by_pallet_id(db, pallet_id)
            
            if not success:
                self.logger.error(f"[订单托盘校验] - ❌ 订单托盘不在库内")
                return False, f"❌ {sql_qrcode_info}"
            else:
                if isinstance(sql_qrcode_info, LocationModel):

                    self.logger.info(f"[订单托盘校验] - ✅ 订单托盘在库内")
                
                    if sql_qrcode_info and sql_qrcode_info.location in [start_location]:
                        self.logger.error(f"[订单托盘校验] - ✅ 订单托盘位置与库位匹配")
                    else:
                        self.logger.error(f"[订单托盘校验] - ❌ 订单托盘位置与库位不匹配")
                        return False, "❌ 订单托盘位置与库位不匹配"
                
                else:
                    return False, f"获取到未知的成功响应类型: {type(sql_qrcode_info)}"
            
            # ---------------------------------------- #
            # base 2: 校验订单起始位置
            # ---------------------------------------- #

            self.logger.info(f"[base 2] 校验订单起始位置")

            if start_location == end_location:
                return False, f"❌ 起始位置与目标位置相同({start_location})，请重新选择"

            buffer_list = [
                "1,3,1", "2,3,1", "3,3,1", "5,3,1", "6,3,1",
                "1,3,2", "2,3,2", "3,3,2", "5,3,2", "6,3,2",
                "1,3,3", "2,3,3", "3,3,3", "5,3,3", "6,3,3",
                "1,3,4", "2,3,4", "3,3,4", "5,3,4", "6,3,4"
                ]
            
            # 校验订单起始位置
            if start_location in buffer_list:
                return False, f"❌ {start_location} 位置为接驳位/缓冲位/电梯位，不能使用此功能操作"
            
            success, location_info = self.location_service.get_location_by_loc(db, start_location)
            if not success:
                self.logger.error(f"[初始位置校验] - ❌ {location_info}")
                return False, f"❌ {location_info}"
            else:
                if isinstance(location_info, List):
                    if location_info.status in ["free", "lift", "highway"]:
                        return False, f"移动目标错误，目标状态为{location_info.status}"
                    else:
                        self.logger.info(f"[初始位置校验] ✅ 初始位置状态 - {location_info.status}")
                        self.logger.info(f"[SYSTEM] 初始位置信息 - id:{location_info.id}, 位置:{location_info.location}, 托盘号:{location_info.pallet_id}, 状态:{location_info.status}")
                else:
                    return False, f"获取到未知的成功响应类型: {type(location_info)}"
            
            # 校验订单目标位置
            if end_location in buffer_list:
                return False, f"❌ {end_location} 位置为接驳位/缓冲位/电梯位，不能使用此功能操作"
            
            success, location_info = self.location_service.get_location_by_loc(db, end_location)
            if not success:
                self.logger.error(f"[目标位置校验] ❌ {location_info}")
                return False, f"❌ {location_info}"
            else:
                if isinstance(location_info, List):
                    if location_info.status in ["occupied", "lift", "highway"]:
                        return False, f"移动目标错误，目标状态为{location_info.status}"
                    else:
                        self.logger.info(f"[目标位置校验] ✅ 目标位置状态 - {location_info.status}")
                        self.logger.info(f"[SYSTEM] 目标位置信息 - id:{location_info.id}, 位置:{location_info.location}, 托盘号:{location_info.pallet_id}, 状态:{location_info.status}")
                else:
                    return False, f"获取到未知的成功响应类型: {type(location_info)}"
            
            # ---------------------------------------- #
            # step 1: 解析目标库位信息
            # ---------------------------------------- #

            self.logger.info("[step 1] 获取目标库位信息")

            car_location = self.car.car_current_location()
            if car_location == "error":
                self.logger.error("❌ 获取穿梭车位置错误")
                return False, "❌ 获取穿梭车位置错误"
            else:
                self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
            
            car_loc = list(map(int, car_location.split(',')))
            car_layer = car_loc[2]
            
            # 获取初始库位信息
            start_loc = list(map(int, start_location.split(',')))
            start_layer = start_loc[2]

            end_loc = list(map(int, end_location.split(',')))
            end_layer = end_loc[2]

            if start_layer != end_layer:
                return False, "❌ 初始层与目标层不一致"
            
            if car_layer != start_layer or car_layer != end_layer:
                return False, f"操作失败，穿梭车层{car_layer}、起点{start_layer}、终点{end_layer}楼层必须保持一致"

            # ---------------------------------------- #
            # step 2: 判断是否需要穿梭车跨层
            # ---------------------------------------- #

            self.logger.info("[step 2] 先让穿梭车跨层")
            
            success, car_move_info = self.device_service.car_cross_layer(task_no, start_layer)
            if success:
                self.logger.info(f"{car_move_info}")
            else:
                self.logger.error(f"{car_move_info}")
                return False, f"{car_move_info}"
            
            # ---------------------------------------- #
            # step 3: 处理阻挡货物
            # ---------------------------------------- #

            self.logger.info("[step 3] 处理出库阻挡货物")

            blocking_nodes = self.get_block_node(start_location, end_location, db)
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
                        
                self.logger.info(f"[SYSTEM] 靠近高速道阻塞点(按距离排序): {do_blocking_nodes}")
                if len(do_blocking_nodes) > 3:
                    self.logger.warning(f"❌ 没有足够的临时存储点操作货物移动 ({start_location}) -> ({end_location})")
                    return False, f"❌ 没有足够的临时存储点操作货物移动 ({start_location}) -> ({end_location})"

                # 定义临时存放点
                temp_storage_nodes = [f"1,3,{end_layer}", f"2,3,{end_layer}", f"3,3,{end_layer}"]
                # 记录移动映射关系，用于将货物移回原位
                move_mapping = {}

                # step 3.2: 处理遮挡货物
                block_taskno = task_no+1
                for i, blocking_node in enumerate(do_blocking_nodes):
                    if i < len(temp_storage_nodes):
                        temp_node = temp_storage_nodes[i]
                        self.logger.info(f"[CAR] 移动({blocking_node})遮挡货物到({temp_node})")
                        move_mapping[blocking_node] = temp_node

                        # 移动货物
                        success, good_move_info = await self.good_move_by_start_end_no_lock(block_taskno, blocking_node, temp_node)
                        if success:
                            self.logger.info(f"{good_move_info}")
                            block_taskno += 3
                        else:
                            self.logger.error(f"{good_move_info}")
                            return False, f"{good_move_info}"

                    else:
                        self.logger.warning(f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})")
                        return False, f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})"
            else:
                self.logger.info("[SYSTEM] 无阻塞节点，直接出库")

            # ---------------------------------------- #
            # step 4: 货物转移
            # ---------------------------------------- #

            self.logger.info(f"[step 4] ({start_location})货物转移到({end_location})")
            
            success, good_move_info = await self.good_move_by_start_end_no_lock(task_no+9, start_location, end_location)
            if success:
                self.device_service.logger.info(f"✅ ({start_location})货物转移到({end_location})成功")
            else:
                self.device_service.logger.error(f"❌ ({start_location})货物转移到({end_location})失败")
                return False, f"❌ ({start_location})货物转移到({end_location})失败"

            # ---------------------------------------- #
            # step 5: 移动遮挡货物返回到原位（按相反顺序）
            # ---------------------------------------- #

            self.logger.info(f"[step 5] 移动遮挡货物返回到原位（按相反顺序）")
            
            block_taskno = task_no+3
            if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
                for blocking_node, temp_node in reversed(list(move_mapping.items())):
                    self.device_service.logger.info(f"[CAR] 移动({temp_node})遮挡货物返回({blocking_node})")
                    
                    # 移动货物
                    success, good_move_info = await self.good_move_by_start_end_no_lock(block_taskno, temp_node, blocking_node)
                    if success:
                        self.logger.info(f"{good_move_info}")
                        block_taskno += 3
                    else:
                        self.logger.error(f"{good_move_info}")
                        return False, f"{good_move_info}"
            else:
                self.logger.info("[SYSTEM] 无阻塞节点返回原位，无需处理")
            
            # ---------------------------------------- #
            # step 6: 数据库更新信息
            # ---------------------------------------- #

            self.logger.info(f"[step 6] 数据库更新信息")
            
            return_list = []
            
            success, sql_info_start = self.location_service.delete_pallet_by_loc(db, start_location)
            if not success:
                self.logger.error(f"[SYSTEM] ❌ {sql_info_start}")
                return False, f"❌ {sql_info_start}"
            else:
                if isinstance(sql_info_start, List):
                    sql_start_returen = {
                        "id": sql_info_start.id,
                        "location": sql_info_start.location,
                        "pallet_id": sql_info_start.pallet_id,
                        "satus": sql_info_start.status
                    }
                    return_list.append(sql_start_returen)
                else:
                    return False, f"❌ 更新托盘号到({start_location})失败"
            
            success, sql_info_end = self.location_service.update_pallet_by_loc(db, end_location, pallet_id)
            if not success:
                self.logger.error(f"[SYSTEM] ❌ {sql_info_end}，更新托盘号到({end_location})失败")
                return False, f"❌ {sql_info_end}"
            else:
                if isinstance(sql_info_end, List):
                    sql_end_returen = {
                        "id": sql_info_end.id,
                        "location": sql_info_end.location,
                        "pallet_id": sql_info_end.pallet_id,
                        "satus": sql_info_end.status
                    }
                    return_list.append(sql_end_returen)
                    return True, return_list
                else:
                    return False, f"获取到未知的成功响应类型: {type(location_info)}"

        finally:
            self.release_lock()