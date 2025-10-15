# devices/car_controller.py

from typing import Any, Dict, List, Optional, Tuple, Union
import time
import asyncio
import logging
logger = logging.getLogger(__name__)

from app.core.config import settings
from app.map_core import PathCustom
from ..connection.connection_base import ConnectionBase
from ..enum import CarStatus, StatusDescription
from app.res_system import PacketBuilder, PacketParser
from app.res_system.res_protocol import (
    CarBaseEnum,
    Debug,
    ErrorHandler,
    FrameType,
    RESProtocol,
    WorkCommand
)

class ControllerBase(ConnectionBase):
    """[穿梭车 - 高级操作类] 基于socket 同步模式。"""

    def __init__(self, CAR_IP: str, CAR_PORT: int):
        """初始化穿梭车客户端。

        Args:
            CAR_IP: plc地址, 如 “192.168.3.30”
            CAR_PORT: plc端口, 如 2504
        """
        self._car_ip = CAR_IP
        self._car_port = CAR_PORT
        super().__init__(self._car_ip, self._car_port)
        self._car_id = self.set_car_id()
        self.builder = PacketBuilder(self._car_id)
        self.parser = PacketParser()
        self.map = PathCustom()

    def set_car_id(self) -> int:
        """[设置_car_id] 用于设置穿梭车ID。

        Returns:
            final_car_id: 最终穿梭车ID
        """
        if self._host == "192.168.8.20":
            final_car_id = 1
        elif self._host == "192.168.8.30":
            final_car_id = 2
        else:
            final_car_id = 0
        return final_car_id

    
    ########################################
    # 发送心跳包 - 读取穿梭车
    ########################################

    def send_heartbeat(self, TIMES: int=3) -> Dict:
        """心跳报文可以获取穿梭车状态。

        Args:
            TIMES: 心跳次数

        Returns:
            Dict: 返回心跳报文解析后的参数
        """
        for i in range(TIMES):
            packet = self.builder.heartbeat()
            self.connect()
            if self.is_connected():
                self.send_message(packet)
                response = self.receive_message()
                if response != b'\x00':
                    msg = self.parser.parse_heartbeat_response(response)
                    self.close()
                    logger.debug(msg)
                    return msg
                else:
                    self.close()
                    logger.error("[CAR] 📰 未收到 [心跳] 响应报文！")

            else:
                self.close()
                logger.error("[CAR] 🚗 穿梭车未连接！")

        
        # 如果循环没有执行（例如 TIMES <= 0），返回默认错误信息
        logger.error("[CAR] ⚠️  心跳发送次数设置错误或未发送心跳！")
        return {
            "car_status": "error",
            "message": "心跳发送次数设置错误或未发送心跳！"
        }

    def car_power(self, times: int=3) -> Dict:
        """[获取穿梭车电量] 发送电量心跳包，获取穿梭车电量。

        Args:
            times: 心跳次数

        Returns:
            car_power_msg: 返回穿梭车电量信息
        """
        for _ in range(times):
            packet = self.builder.build_heartbeat(FrameType.HEARTBEAT_WITH_BATTERY)
            self.connect()
            if self.is_connected():
                self.send_message(packet)
                response = self.receive_message()
                if response != b'\x00':
                    self.close()
                    msg = self.parser.parse_hb_power_response(response)
                    logger.debug(msg)
                    
                    return {
                        'cmd_no': msg['cmd_no'],
                        'resluct': msg['resluct'],
                        'current_location': msg['current_location'],
                        'current_segment': msg['current_segment'],
                        'cur_barcode': msg['cur_barcode'],
                        'car_status': CarStatus.get_info_by_value(msg['car_status']).get('description'),
                        'pallet_status': msg['pallet_status'],
                        'reserve_status': msg['reserve_status'],
                        'drive_direction': msg['drive_direction'],
                        'status_description': StatusDescription.get_info_by_value(msg['status_description']).get('description'),
                        'have_pallet': msg['have_pallet'],
                        'driver_warning': msg['driver_warning'],
                        'power': msg['power'],
                    }
                else:
                    self.close()
                    logger.error("[CAR] ⚡️ 未收到 [电量心跳] 响应报文！")
            else:
                self.close()
                logger.error("[CAR] 🚗 穿梭车未连接！")
        
        # 如果循环没有执行（例如 TIMES <= 0），返回默认错误信息
        logger.error("[CAR] ⚠️ 心跳发送次数设置错误或未发送心跳！")
        return {
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
    
    def car_status(self, times: int=3) -> Dict:
        """[获取穿梭车状态] 发送心跳报文，获取穿梭车状态信息。

        Args:
            times: 心跳次数

        Returns:
            Dict: 穿梭车状态信息
        """
        heartbeat_msg = self.send_heartbeat(times)
        if heartbeat_msg:
            car_status_info = CarStatus.get_info_by_value(heartbeat_msg['car_status'])
            car_status = heartbeat_msg['car_status']
            name = car_status_info.get('description')
            description = CarStatus.get_info_by_value(heartbeat_msg['status_description'])
            logger.info(f"[CAR] 穿梭车状态码: {car_status}时, 穿梭车状态: {name}, 状态描述: {description}")
            return {
                'car_status': car_status,
                'name': name,
                'description': description
                }
        else:
            return {
                'car_status': "error",
                'name': "error",
                'description': "error"
                }

    def car_current_location(self, TIMES: int=3) -> str:
        """获取小车位置。

        Args:
            TIMES: 心跳次数
        
        Returns:
            car_location: 小车当前位置, 例如: "6,3,1"
        """
        heartbeat_msg = self.send_heartbeat(TIMES)
        if heartbeat_msg["car_status"] == "error":
            return "error"
        else:
            location_info = heartbeat_msg['current_location']
            car_location = f"{location_info[0]},{location_info[1]},{location_info[2]}"
            return car_location
    

    def wait_car_move_complete_by_location_sync(
            self,
            LOCATION: str,
            TIMEOUT: float = settings.CAR_ACTION_TIMEOUT
            ) -> bool:
        """[同步] 等待穿梭车移动到指定位置

        Args:
            LOCATION: 目标位置 如 "6,3,1"

        Returns:
            bool: 用于确认等到的标志
        """
        
        target_loc = list(map(int, LOCATION.split(',')))
        target_x, target_y, target_z = target_loc[0], target_loc[1], target_loc[2]
        logger.info(f"[CAR] ⏳ 等待小车移动到位置: {LOCATION}")

        time.sleep(2)
        start_time = time.time()
        
        while True:
            # 获取小车当前位置
            car_location = self.car_current_location()
            car_cur_loc = list(map(int, car_location.split(',')))
            car_x, car_y, car_z = car_cur_loc[0], car_cur_loc[1], car_cur_loc[2]
            
            if (car_x == target_x) and (car_y == target_y) and (car_z == target_z):
                logger.info(f"[CAR] ✅ 小车已到达目标位置 {LOCATION}")
                return True
            
            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > TIMEOUT:
                logger.error(f"❌ 超时错误: 等待🚗动作超时 ({TIMEOUT}s)")
                return False
            
            # 等待一段时间再次检查
            time.sleep(1)

    async def wait_car_move_complete_by_location(
            self,
            LOCATION: str,
            TIMEOUT: float = settings.CAR_ACTION_TIMEOUT
            ) -> bool:
        """[异步] 等待穿梭车移动到指定位置

        Args:
            LOCATION: 目标位置 如 "6,3,1"

        Returns:
            bool: 用于确认等到的标志
        """
        
        target_loc = list(map(int, LOCATION.split(',')))
        target_x, target_y, target_z = target_loc[0], target_loc[1], target_loc[2]
        logger.info(f"[CAR] ⏳ 等待小车移动到位置: {LOCATION}")

        await asyncio.sleep(2)
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 获取小车当前位置
            car_location = await asyncio.to_thread(self.car_current_location)
            car_cur_loc = list(map(int, car_location.split(',')))
            car_x, car_y, car_z = car_cur_loc[0], car_cur_loc[1], car_cur_loc[2]
            
            if (car_x == target_x) and (car_y == target_y) and (car_z == target_z):
                logger.info(f"[CAR] ✅ 小车已到达目标位置 {LOCATION}")
                return True
            
            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > TIMEOUT:
                logger.error(f"❌ 超时错误: 等待🚗动作超时 ({TIMEOUT}s)")
                return False
            
            # 等待一段时间再次检查
            await asyncio.sleep(1)

    
    ########################################
    # 发送任务包 - 操作穿梭车
    ########################################

    def send_work_command(
            self,
            task_no: int,
            cmd_no: int,
            cmd: bytes,
            cmd_param: list=[0,0,0,0]
    ) -> bool:
        """[穿梭车工作指令] 发送工作指令包。
        
        Args:
            task_no (int): 任务号
            cmd_no (int): 指令号
            cmd (bytes): 指令
            cmd_param (list, optional): 参数. Defaults to [0,0,0,0].
        
        Returns:
            bool: 是否发送成功
        """
        packet = self.builder.build_work_command(
            task_number=task_no,
            command_number=cmd_no,
            command=cmd,
            command_param=cmd_param
            )
        logger.debug(packet)
        if self.connect():
            self.send_message(packet)
            response = self.receive_message()
            logger.debug(response)
            if response:
                msg = self.parser.parse_command_response(response)
                logger.debug(msg)
                self.close()
                return True
            else:
                logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                self.close()
                return False
        else:
            logger.error("[CAR] 位置修改失败")
            self.close()
            return False
    
    def change_car_location(self, TASK_NO: int, CAR_LOCATION: str) -> bool:
        """[修改穿梭车位置] 发送指令包, 修改穿梭车坐标。
        
        Args:
            TASK_NO: 任务号
            CAR_LOCATION: 小车位置 如，"6,3,1"
        """
        packet = self.builder.location_change(TASK_NO, CAR_LOCATION)
        logger.debug(packet)
        if self.connect():
            self.send_message(packet)
            response = self.receive_message()
            logger.debug(response)
            if response:
                msg = self.parser.parse_command_response(response)
                logger.debug(msg)
                self.close()
                return True
            else:
                logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                self.close()
                return False
        else:
            logger.error("[CAR] 位置修改失败")
            self.close()
            return False

    def car_move(self, TASK_NO: int, TARGET_LOCATION: str) -> bool:
        """穿梭车移动。

        Args:
            TASK_NO: 任务号(1-255)
            TARGET_LOCATION: 小车移动目标 如，"6,3,1"
        """

        # 获取小车当前坐标
        heartbeat_msg = self.send_heartbeat(1)
        location_info = heartbeat_msg['current_location']
        car_current_location = f"{location_info[0]},{location_info[1]},{location_info[2]}"
        logger.info(f"[CAR] 穿梭车当前位置: {car_current_location}")
        if car_current_location == TARGET_LOCATION:
            return True
        
        # 创建移动路径
        # segments = [
        #     (6,3,1,0),
        #     (4,3,1,5),
        #     (4,1,1,6),
        #     (1,1,1,0)
        #             ]
        segments = self.map.build_segments(car_current_location, TARGET_LOCATION)
        if isinstance(segments, list):
            logger.info(f"[CAR] 创建移动路径: {segments}")
        else:
            logger.error(f"[CAR] 无法创建移动路径: {segments}")
            return False

        # 发送任务报文
        task_packet = self.builder.build_task(TASK_NO, segments)
        if self.connect():
            self.send_message(task_packet)
            task_response = self.receive_message()
            if task_response:
                # 发送任务确认执行报文
                do_packet = self.builder.do_task(TASK_NO, segments)
                self.send_message(do_packet)
                do_response = self.receive_message()
                if do_response:
                    msg = self.parser.parse_task_response(do_response)
                    logger.debug(msg)
                    self.close()
                    return True
                else:
                    logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                    self.close()
                    return False
            else:
                logger.error("[CAR] 📰 未收到 [任务] 响应报文！")
                self.close()
                return False
        else:
            logger.error("[CAR] 🚗 穿梭车未连接！")
            self.close()
            return False

    def add_pick_drop_actions(self, POINT_LIST: list) -> list:
        """[添加货物操作动作] 在路径列表的起点和终点添加货物操作动作。
        
        Args:
            POINT_LIST: generate_point_list()生成的路径列表
        
        Returns:
            list: 修改后的路径列表（起点动作=1提起，终点动作=2放下）
        """
        # 确保路径至少有两个点
        if len(POINT_LIST) < 2:
            return POINT_LIST
        
        # 创建列表副本防止修改原数据
        new_list = [tuple(point) for point in POINT_LIST]
        
        # 修改起点动作（索引0）为1（提起货物）
        new_list[0] = tuple(new_list[0][:3]) + (1,)
        
        # 修改终点动作（索引-1）为2（放下货物）
        new_list[-1] = tuple(new_list[-1][:3]) + (2,)
        
        return new_list
    

    def good_move(self, TASK_NO: int, TARGET_LOCATION: str) -> bool:
        """[穿梭车带货移动] 发送移动货物任务
        
        Args:
            TASK_NO: 任务号(1-255)
            TARGET_LOCATION: 小车移动目标 如 "1,1,1"
        """

        # 获取小车当前坐标
        heartbeat_msg = self.send_heartbeat()
        location_info = heartbeat_msg['current_location']
        car_current_location = f"{location_info[0]},{location_info[1]},{location_info[2]}"
        logger.info(f"[CAR] 穿梭车当前位置: {car_current_location}")
        if car_current_location == TARGET_LOCATION:
            return True
        
        # 创建移动路径
        # segments = [
        #     (6,3,1,0),
        #     (4,3,1,5),
        #     (4,1,1,6),
        #     (1,1,1,0)
        #             ]
        car_move_segments = self.map.build_segments(car_current_location, TARGET_LOCATION)
        segments = self.add_pick_drop_actions(car_move_segments)
        if isinstance(segments, list):
            logger.info(f"[CAR] 创建移动路径: {segments}")
        else:
            logger.error(f"[CAR] 无法创建移动路径: {segments}")
            return False

        # 开启连接
        if self.connect():
            # 发送整体任务报文
            task_packet = self.builder.build_task(TASK_NO, segments)
            self.send_message(task_packet)
            # 接收整体任务报文
            task_response = self.receive_message()
            if task_response:
                task_msg = self.parser.parse_task_response(task_response)
                logger.debug(f"[CAR] 解析整体任务响应结果: {task_msg}")
                
                # 发送任务确认执行报文
                do_packet = self.builder.do_task(TASK_NO, segments)
                self.send_message(do_packet)
                # 接收任务确认执行报文
                do_response = self.receive_message()
                if do_response:
                    do_msg = self.parser.parse_task_response(do_response)
                    logger.debug(f"[CAR] 解析任务执行指令响应结果: {do_msg}")
                    # 关闭连接
                    self.close()
                    return True
                else:
                    logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                    self.close()
                    return False
            else:
                logger.error("[CAR] 📰 未收到 [任务] 响应报文！")
                self.close()
                return False
        else:
            logger.error("[CAR] 🚗 穿梭车未连接！")
            self.close()
            return False