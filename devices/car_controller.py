# devices/car_controller.py

from typing import Union, Any
import asyncio

from .car_connection_module import CarConnectionBase
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
        super().__init__(CAR_IP, CAR_PORT)
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

    async def send_heartbeat(self, TIMES: int) -> Any:
        """
        [发送心跳包] - 心跳报文可以获取穿梭车状态

        ::: param :::
            TIMES: 心跳次数

        ::: return :::
            msg: 返回心跳报文解析后的参数
        """
        for i in range(TIMES):
            packet = self.builder.heartbeat()
            if await self.connect():
                await self.send_message(packet)
                response = await self.receive_message()
                if response:
                    msg = self.parser.parse_heartbeat_response(response)
                    self.logger.info(msg)
                    await self.close()
                    return msg
                else:
                    self.logger.error("[CAR] 📰 未收到 [心跳] 响应报文！")
                    await self.close()
                    return {
                        "status": False,
                        "msg": "未收到 [心跳] 响应报文！"
                    }
            else:
                self.logger.error("[CAR] 🚗 穿梭车未连接！")
                await self.close()
                return {
                        "status": False,
                        "msg": "穿梭车未连接！"
                    }

    async def car_power(self, TIMES: int) -> Any:
        """
        [获取穿梭车电量] - 发送电量心跳包，获取穿梭车电量

        ::: param :::
            TIMES: 心跳次数

        ::: return :::
            car_power_msg: 返回穿梭车电量信息
        """
        for i in range(TIMES):
            packet = self.builder.build_heartbeat(FrameType.HEARTBEAT_WITH_BATTERY)
            if await self.connect():
                await self.send_message(packet)
                response = await self.receive_message()
                if response:
                    msg = self.parser.parse_hb_power_response(response)
                    self.logger.info(msg)
                    await self.close()
                    car_power_msg = msg['power']
                    return car_power_msg
                else:
                    self.logger.error("[CAR] ⚡️ 未收到 [电量心跳] 响应报文！")
                    await self.close()
                    return False
            else:
                self.logger.error("[CAR] 🚗 穿梭车未连接！")
                await self.close()
                return False
    
    async def car_status(self, TIMES: int) -> dict:
        """
        [获取穿梭车状态] - 发送心跳报文，获取穿梭车状态信息

        ::: param :::
            TIMES: 心跳次数
        ::: return :::
            car_status: 穿梭车状态信息
        """
        heartbeat_msg = await self.send_heartbeat(TIMES)
        car_status = CarStatus.get_info_by_value(heartbeat_msg['car_status'])
        self.logger.info(f"[CAR] 穿梭车状态码: {heartbeat_msg['car_status']}时, 穿梭车状态: {car_status['name']}, 状态描述: {car_status['description']}")
        return {
             'status': heartbeat_msg['car_status'],
             'name': car_status['name'],
             'description': car_status['description']
             }

    async def car_current_location(self, TIMES: int) -> str:
        """
        [获取小车位置]

        ::: param :::
            TIMES: 心跳次数
        
        ::: return :::
            car_location: 小车当前位置, 例如: "6,3,1"
        """
        heartbeat_msg = await self.send_heartbeat(TIMES)
        location_info = heartbeat_msg['current_location']
        car_location = f"{location_info[0]},{location_info[1]},{location_info[2]}"
        return car_location
    
    async def wait_car_move_complete_by_location(self, LOCATION: str) -> bool:
        """
        [穿梭车等待器] - 等待穿梭车移动到指定位置

        ::: param :::
            LOCATION: 目标位置 如 "6,3,1"

        ::: return :::
            用于确认等到的标志 bool
        """
        target_loc = list(map(int, LOCATION.split(',')))
        target_x, target_y, target_z = target_loc[0], target_loc[1], target_loc[2]
        
        self.logger.info(f"[CAR] ⏳ 等待小车移动到位置: {LOCATION}")
        
        while True:
            # 获取小车当前位置
            car_location = await self.car_current_location(1)
            car_cur_loc = list(map(int, car_location.split(',')))
            car_x, car_y, car_z = car_cur_loc[0], car_cur_loc[1], car_cur_loc[2]
            
            if (car_x == target_x) and (car_y == target_y) and (car_z == target_z):
                self.logger.info("[CAR] ✅ 小车已到达目标位置")
                return True
            
            await asyncio.sleep(1)

    
    ########################################
    # 发送任务包 - 操作穿梭车
    ########################################

    async def change_car_location(self, TASK_NO: int, CAR_LOCATION: str) -> bool:
        """
        [修改穿梭车位置] - 发送指令包, 修改穿梭车坐标
        
        ::: param :::
            TASK_NO: 任务号
            CAR_LOCATION: 小车位置 如，"6,3,1"
        """
        packet = self.builder.location_change(TASK_NO, CAR_LOCATION)
        self.logger.info(packet)
        if await self.connect():
            await self.send_message(packet)
            response = await self.receive_message()
            self.logger.info(response)
            if response:
                msg = self.parser.parse_command_response(response)
                self.logger.info(msg)
                await self.close()
                return True
            else:
                self.logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                await self.close()
                return False
        else:
            self.logger.error("[CAR] 位置修改失败")
            await self.close()
            return False

    async def car_move(self, TARGET_LOCATION: str) -> bool:
        """
        [穿梭车移动]

        ::: param :::
            TARGET_LOCATION: 小车移动目标 如，"6,3,1"
        """
        # 创建任务号
        import random
        task_no = random.randint(1, 255)

        # 获取小车当前坐标
        heartbeat_msg = await self.send_heartbeat(1)
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
        task_packet = self.builder.build_task(task_no, segments)
        if await self.connect():
            await self.send_message(task_packet)
            response = await self.receive_message()
            if response:
                # 发送任务确认执行报文
                do_packet = self.builder.do_task(task_no, segments)
                await self.send_message(do_packet)
                response = await self.receive_message()
                if response:
                    msg = self.parser.parse_task_response(response)
                    self.logger.info(msg)
                    await self.close()
                    return True
                else:
                    self.logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                    await self.close()
                    return False
            else:
                self.logger.error("[CAR] 📰 未收到 [任务] 响应报文！")
                await self.close()
                return False
        else:
            self.logger.error("[CAR] 🚗 穿梭车未连接！")
            await self.close()
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
    

    async def good_move(self, TARGET_LOCATION: str) -> bool:
        """
        [穿梭车带货移动] - 发送移动货物任务
        
        :::: param :::
            TARGET_LOCATION: 小车移动目标 如 "1,1,1"
        """
        # 创建任务号
        import random
        task_no = random.randint(1, 255)

        # 获取小车当前坐标
        heartbeat_msg = await self.send_heartbeat(1)
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

        # 发送任务报文
        task_packet = self.builder.build_task(task_no, segments)
        if await self.connect():
            await self.send_message(task_packet)
            response = await self.receive_message()
            if response:
                # 发送任务确认执行报文
                do_packet = self.builder.do_task(task_no, segments)
                await self.send_message(do_packet)
                response = await self.receive_message()
                if response:
                    msg = self.parser.parse_task_response(response)
                    self.logger.info(msg)
                    await self.close()
                    return True
                else:
                    self.logger.error("[CAR] 📰 未收到 [指令] 响应报文！")
                    await self.close()
                    return False
            else:
                self.logger.error("[CAR] 📰 未收到 [任务] 响应报文！")
                await self.close()
                return False
        else:
            self.logger.error("[CAR] 🚗 穿梭车未连接！")
            await self.close()
            return False