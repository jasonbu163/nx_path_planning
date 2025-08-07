# devices/car_controller.py

from typing import Union, Any
import time
import asyncio

from config import CAR_ACTION_TIMEOUT
from .car_connection_module import CarConnectionBase, CarConnection
from map_core import PathCustom
from .car_enum import CarStatus
from res_protocol_system import (
    PacketBuilder,
    PacketParser
)
from res_protocol_system.RESProtocol import (
    CarBaseEnum,
    Debug,
    ErrorHandler,
    FrameType,
    RESProtocol,
    WorkCommand
)

class CarController(CarConnectionBase):
    """
    [穿梭车 - 高级操作类]
    """

    def __init__(self, CAR_IP: str, CAR_PORT: int):
        """
        [初始化穿梭车客户端]

        ::: param :::
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
        """
        [设置_car_id] - 用于设置穿梭车ID

        ::: return ::: 
            final_car_id: 最终穿梭车ID
        """
        if self._host == "192.168.8.10":
            final_car_id = 1
        elif self._host == "192.168.8.30":
            final_car_id = 2
        else:
            final_car_id = 0
        return final_car_id

    
    ########################################
    # 发送心跳包 - 读取穿梭车
    ########################################

    def send_heartbeat(self, TIMES: int=3) -> dict:
        """
        [发送心跳包] - 心跳报文可以获取穿梭车状态

        ::: param :::
            TIMES: 心跳次数

        ::: return :::
            msg: 返回心跳报文解析后的参数
        """
        for i in range(TIMES):
            packet = self.builder.heartbeat()
            self.connect()
            if self.is_connected():
                time.sleep(1)
                self.send_message(packet)
                response = self.receive_message()
                if response != b'\x00':
                    self.close()
                    msg = self.parser.parse_heartbeat_response(response)
                    self.logger.info(msg)
                    return msg
                else:
                    self.close()
                    self.logger.error("[CAR] 📰 未收到 [心跳] 响应报文！")
                    return {
                        "car_status": "error",
                        "message": "未收到 [心跳] 响应报文！"
                    }
            else:
                self.close()
                self.logger.error("[CAR] 🚗 穿梭车未连接！")
                return {
                        "car_status": "error",
                        "message": "穿梭车未连接！"
                    }
        
        # 如果循环没有执行（例如 TIMES <= 0），返回默认错误信息
        self.logger.error("[CAR] ⚠️  心跳发送次数设置错误或未发送心跳！")
        return {
            "car_status": "error",
            "message": "心跳发送次数设置错误或未发送心跳！"
        }

    def car_power(self, TIMES: int=3) -> Any:
        """
        [获取穿梭车电量] - 发送电量心跳包，获取穿梭车电量

        ::: param :::
            TIMES: 心跳次数

        ::: return :::
            car_power_msg: 返回穿梭车电量信息
        """
        for i in range(TIMES):
            packet = self.builder.build_heartbeat(FrameType.HEARTBEAT_WITH_BATTERY)
            self.connect()
            if self.is_connected():
                self.send_message(packet)
                response = self.receive_message()
                if response:
                    self.close()
                    msg = self.parser.parse_hb_power_response(response)
                    self.logger.info(msg)
                    car_power_msg = msg['power']
                    return car_power_msg
                else:
                    self.close()
                    self.logger.error("[CAR] ⚡️ 未收到 [电量心跳] 响应报文！")
                    return None
            else:
                self.close()
                self.logger.error("[CAR] 🚗 穿梭车未连接！")
                return None
    
    def car_status(self, TIMES: int=3) -> dict:
        """
        [获取穿梭车状态] - 发送心跳报文，获取穿梭车状态信息

        ::: param :::
            TIMES: 心跳次数
        ::: return :::
            car_status: 穿梭车状态信息
        """
        heartbeat_msg = self.send_heartbeat(TIMES)
        if heartbeat_msg:
            car_status = CarStatus.get_info_by_value(heartbeat_msg['car_status'])
            self.logger.info(f"[CAR] 穿梭车状态码: {heartbeat_msg['car_status']}时, 穿梭车状态: {car_status['name']}, 状态描述: {car_status['description']}")
            return {
                'car_status': heartbeat_msg['car_status'],
                'name': car_status['name'],
                'description': car_status['description']
                }
        else:
            return {
                'car_status': "error",
                'name': "未知",
                'description': "未知"
                }

    def car_current_location(self, TIMES: int=3) -> str:
        """
        [获取小车位置]

        ::: param :::
            TIMES: 心跳次数
        
        ::: return :::
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
            TIMEOUT: float = CAR_ACTION_TIMEOUT
            ) -> bool:
        """
        [同步 - 穿梭车等待器] 等待穿梭车移动到指定位置

        ::: param :::
            LOCATION: 目标位置 如 "6,3,1"

        ::: return :::
            用于确认等到的标志 bool
        """
        
        target_loc = list(map(int, LOCATION.split(',')))
        target_x, target_y, target_z = target_loc[0], target_loc[1], target_loc[2]
        self.logger.info(f"[CAR] ⏳ 等待小车移动到位置: {LOCATION}")

        time.sleep(2)
        start_time = time.time()
        
        while True:
            # 获取小车当前位置
            car_location = self.car_current_location(1)
            car_cur_loc = list(map(int, car_location.split(',')))
            car_x, car_y, car_z = car_cur_loc[0], car_cur_loc[1], car_cur_loc[2]
            
            if (car_x == target_x) and (car_y == target_y) and (car_z == target_z):
                self.logger.info(f"[CAR] ✅ 小车已到达目标位置 {LOCATION}")
                return True
            
            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > TIMEOUT:
                self.logger.info(f"❌ 超时错误: 等待🚗动作超时 ({TIMEOUT}s)")
                return False
            
            # 等待一段时间再次检查
            time.sleep(1)

    async def wait_car_move_complete_by_location(
            self,
            LOCATION: str,
            TIMEOUT: float = CAR_ACTION_TIMEOUT
            ) -> bool:
        """
        [异步 - 穿梭车等待器] 等待穿梭车移动到指定位置

        ::: param :::
            LOCATION: 目标位置 如 "6,3,1"

        ::: return :::
            用于确认等到的标志 bool
        """
        
        target_loc = list(map(int, LOCATION.split(',')))
        target_x, target_y, target_z = target_loc[0], target_loc[1], target_loc[2]
        self.logger.info(f"[CAR] ⏳ 等待小车移动到位置: {LOCATION}")

        await asyncio.sleep(2)
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 获取小车当前位置
            car_location = await asyncio.to_thread(self.car_current_location)
            car_cur_loc = list(map(int, car_location.split(',')))
            car_x, car_y, car_z = car_cur_loc[0], car_cur_loc[1], car_cur_loc[2]
            
            if (car_x == target_x) and (car_y == target_y) and (car_z == target_z):
                self.logger.info(f"[CAR] ✅ 小车已到达目标位置 {LOCATION}")
                return True
            
            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > TIMEOUT:
                self.logger.info(f"❌ 超时错误: 等待🚗动作超时 ({TIMEOUT}s)")
                return False
            
            # 等待一段时间再次检查
            await asyncio.sleep(1)

    
    ########################################
    # 发送任务包 - 操作穿梭车
    ########################################

    def change_car_location(self, TASK_NO: int, CAR_LOCATION: str) -> bool:
        """
        [修改穿梭车位置] - 发送指令包, 修改穿梭车坐标
        
        ::: param :::
            TASK_NO: 任务号
            CAR_LOCATION: 小车位置 如，"6,3,1"
        """
        packet = self.builder.location_change(TASK_NO, CAR_LOCATION)
        self.logger.info(packet)
        if self.connect():
            self.send_message(packet)
            response = self.receive_message()
            self.logger.info(response)
            if response:
                msg = self.parser.parse_command_response(response)
                self.logger.info(msg)
                self.close()
                return True
            else:
                self.logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                self.close()
                return False
        else:
            self.logger.error("[CAR] 位置修改失败")
            self.close()
            return False

    def car_move(self, TASK_NO: int, TARGET_LOCATION: str) -> bool:
        """
        [穿梭车移动]

        ::: param :::
            TASK_NO: 任务号(1-255)
            TARGET_LOCATION: 小车移动目标 如，"6,3,1"
        """

        # 获取小车当前坐标
        heartbeat_msg = self.send_heartbeat(1)
        location_info = heartbeat_msg['current_location']
        car_current_location = f"{location_info[0]},{location_info[1]},{location_info[2]}"
        self.logger.info(f"[CAR] 穿梭车当前位置: {car_current_location}")
        
        # 创建移动路径
        # segments = [
        #     (6,3,1,0),
        #     (4,3,1,5),
        #     (4,1,1,6),
        #     (1,1,1,0)
        #             ]
        segments = self.map.build_segments(car_current_location, TARGET_LOCATION)
        if isinstance(segments, list):
            self.logger.info(f"[CAR] 创建移动路径: {segments}")
        else:
            self.logger.error(f"[CAR] 无法创建移动路径: {segments}")
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
                    self.logger.info(msg)
                    self.close()
                    return True
                else:
                    self.logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                    self.close()
                    return False
            else:
                self.logger.error("[CAR] 📰 未收到 [任务] 响应报文！")
                self.close()
                return False
        else:
            self.logger.error("[CAR] 🚗 穿梭车未连接！")
            self.close()
            return False

    def add_pick_drop_actions(self, POINT_LIST: list) -> list:
        """
        [添加货物操作动作] - 在路径列表的起点和终点添加货物操作动作
        
        ::: param :::
            POINT_LIST: generate_point_list()生成的路径列表
        
        ::: return :::
            new_list: 修改后的路径列表（起点动作=1提起，终点动作=2放下）
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
        """
        [穿梭车带货移动] - 发送移动货物任务
        
        :::: param ::
            TASK_NO: 任务号(1-255)
            TARGET_LOCATION: 小车移动目标 如 "1,1,1"
        """

        # 获取小车当前坐标
        heartbeat_msg = self.send_heartbeat()
        location_info = heartbeat_msg['current_location']
        car_current_location = f"{location_info[0]},{location_info[1]},{location_info[2]}"
        self.logger.info(f"[CAR] 穿梭车当前位置: {car_current_location}")
        
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
            self.logger.info(f"[CAR] 创建移动路径: {segments}")
        else:
            self.logger.error(f"[CAR] 无法创建移动路径: {segments}")
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
                self.logger.info(f"[CAR] 解析整体任务响应结果: {task_msg}")
                
                # 发送任务确认执行报文
                do_packet = self.builder.do_task(TASK_NO, segments)
                self.send_message(do_packet)
                # 接收任务确认执行报文
                do_response = self.receive_message()
                if do_response:
                    do_msg = self.parser.parse_task_response(do_response)
                    self.logger.info(f"[CAR] 解析任务执行指令响应结果: {do_msg}")
                    # 关闭连接
                    self.close()
                    return True
                else:
                    self.logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                    self.close()
                    return False
            else:
                self.logger.error("[CAR] 📰 未收到 [任务] 响应报文！")
                self.close()
                return False
        else:
            self.logger.error("[CAR] 🚗 穿梭车未连接！")
            self.close()
            return False