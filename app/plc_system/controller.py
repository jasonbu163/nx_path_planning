# devices/plc_controller.py

import time
from typing import Union
import asyncio

import struct

from .connection import ConnectionAsync
from .enum import DB_2, DB_9, DB_11, DB_12, FLOOR_CODE, LIFT_TASK_TYPE

class PLCController(ConnectionAsync):
    """PLC高级操作类"""
    
    def __init__(self, plc_ip: str):
        """初始化PLC客户端。

        Args:
            plc_ip: plc地址, 如 “192.168.3.10”
        """
        self._plc_ip = plc_ip
        super().__init__(self._plc_ip)

    # 二进制字符串转字节码
    def binary2bytes(self, binary_str) -> bytes:
        """二进制字符串转字节码。

        Args:
            binary_str: 二进制字符串

        Returns:
            bytes: 字节码
        """
        value = int(binary_str, 2)
        return struct.pack('!B', value)

    ########################################################
    ##################### 电梯相关函数 #######################
    ########################################################

    def plc_checker(self) -> bool:
        """PLC校验器。
        
        在plc连接成功之后，必须使用plc_checker进行校验，否则会导致设备安全事故。
        """
        lift_fault = self.read_bit(11, DB_11.FAULT.value)
        lift_auto_mode = self.read_bit(11, DB_11.AUTO_MODE.value)
        lift_remote_online = self.read_bit(2, DB_2.REMOTE_ONLINE.value)
        conveyor_online = self.read_bit(2, DB_2.CONVEYOR_ONLINE.value)
        
        self.logger.info(f"{DB_11.FAULT.description} - {DB_11.__name__} - {DB_11.FAULT.value} - {lift_fault}")
        self.logger.info(f"{DB_11.AUTO_MODE.description} - {DB_11.__name__} - {DB_11.AUTO_MODE.value} - {lift_auto_mode}")
        self.logger.info(f"{DB_2.REMOTE_ONLINE.description} - {DB_2.__name__} - {DB_2.REMOTE_ONLINE.value} - {lift_remote_online}")
        self.logger.info(f"{DB_2.CONVEYOR_ONLINE.description} - {DB_2.__name__} - {DB_2.CONVEYOR_ONLINE.value} - {conveyor_online}")
        if lift_fault==0 and lift_auto_mode==1 and lift_remote_online==1 and conveyor_online==1:
            self.logger.info("✅ [PLC] PLC就绪")
            return True
        else:
            self.logger.error("❌ [PLC] PLC错误，请检查设备状态")
            return False
    
    def get_lift(self) -> int:
        """获取电梯当前层。

        Returns:
            int: 层数, 如 1层为 1
        """
        # 读取提升机所在层
        db = self.read_db(11, DB_11.CURRENT_LAYER.value, 2)
        # 返回解码的数据
        return struct.unpack('!H', db)[0]
        # 返回原数据
        # return db

    def get_lift_last_taskno(self) -> int:
        """获取电梯上一次任务号。

        Returns:
            int: 任务号, 如 12
        """
        # 读取提升机所在层
        db = self.read_db(9, DB_9.LAST_TASK_NO.value, 2)
        # 返回解码的数据
        return struct.unpack('!H', db)[0]
        # 返回原数据
        # return db
    
    def lift_move(
            self,
            task_type: int,
            task_no: int,
            end_floor: int
    ) -> None:
        """控制电梯到达目标楼层。

        Args:
            task_type: 任务类型
            task_no: 任务号
            end_floor: 目标层
        """

        # 任务号检测
        lift_last_taskno = self.get_lift_last_taskno()
        if lift_last_taskno == task_no:
            task_no += 1
            self.logger.warning(f"[LIFT] 当前任务号和新任务号一致，调整任务号为 - {task_no}")
        
        type = struct.pack('!H', task_type)
        num = struct.pack('!H', task_no)
        # start = struct.pack('!H', start_floor)
        # start = self.get_lift() # 获取电梯所在层
        end = struct.pack('!H', end_floor)

        # 任务类型
        self.write_db(12, DB_12.TASK_TYPE.value, type)
        # 任务号
        self.write_db(12, DB_12.TASK_NUMBER.value, num)
        # 起始层 起始位被电气部份屏蔽 可以不输入
        # self.write_db(12, PLCAddress.START_LAYER.value, start_floor)
        # 目标层
        self.write_db(12, DB_12.TARGET_LAYER.value, end)
        

    def lift_move_by_layer_sync(
            self,
            task_no: int,
            layer: int
    ) -> bool:
        """[同步] 电梯移动操作。

        Args:
            task_no (int): 任务号
            layer (int): 楼层
        
        Returns:
            bool: 指令发送是否成功
        """

        # 任务号检测
        lift_last_taskno = self.get_lift_last_taskno()
        if lift_last_taskno == task_no:
            task_no += 1
            self.logger.warning(f"[LIFT] 当前任务号和新任务号一致，调整任务号为 - {task_no}")
        
        # 任务识别
        lift_running = self.read_bit(11, DB_11.RUNNING.value)
        lift_idle = self.read_bit(11, DB_11.IDLE.value)
        lift_no_cargo = self.read_bit(11, DB_11.NO_CARGO.value)
        lift_has_cargo = self.read_bit(11, DB_11.HAS_CARGO.value)
        lift_has_car = self.read_bit(11, DB_11.HAS_CAR.value)

        self.logger.info(f"[LIFT] 电梯状态 - 电梯运行中:{lift_running} 电梯是否空闲:{lift_idle} 电梯是否无货:{lift_no_cargo} 电梯是否有货:{lift_has_cargo} 电梯是否有车:{lift_has_car} ")

        if layer not in [1,2,3,4]:
            self.logger.error("[LIFT] ❌ 楼层错误")
            return False
        
        else:
            if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
                self.lift_move(LIFT_TASK_TYPE.IDEL, task_no, layer)
                self.logger.info("[LIFT] ✅ 电梯(空载)移动指令已经发送")
                return True
            
            elif lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==1:
                self.lift_move(LIFT_TASK_TYPE.CAR, task_no, layer)
                self.logger.info("[LIFT] ✅ 电梯(载车)移动指令已经发送")
                return True

            elif lift_running==0 and lift_idle==1 and lift_no_cargo==0 and lift_has_cargo==1 and lift_has_car==0:                
                self.lift_move(LIFT_TASK_TYPE.GOOD, task_no, layer)
                self.logger.info("[LIFT] ✅ 电梯(载货)移动指令已经发送")
                return True
            
            elif lift_running==0 and lift_idle==1 and lift_no_cargo==0 and lift_has_cargo==1 and lift_has_car==1:                
                self.lift_move(LIFT_TASK_TYPE.GOOD_CAR, task_no, layer)
                self.logger.info("[LIFT] ✅ 电梯(载货和车)移动指令已经发送")
                return True
            
            else:
                time.sleep(3)
                self.logger.error(f"[LIFT] 未知状态，电梯到达 {self.get_lift()} 层")
                return False
            
    def wait_lift_move_complete_by_location_sync(self) -> bool:
        """[同步] 电梯工作等待器。

        Returns:
            bool: 等待状态
        """
        self.logger.info("[LIFT] 🚧 电梯工作中...")
                
        if self.wait_for_bit_change_sync(11, DB_11.RUNNING.value, 0):
            self.logger.info(f"[LIFT] ✅ 电梯工作完毕")
        else:
            self.logger.error("[LIFT] ❌ 电梯工作失败")
            return False

        # 读取提升机是否空闲
        if self.read_bit(11, DB_11.IDLE.value):
            self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
            self.logger.info(f"[LIFT] ✅ 写入电梯到位状态")
            time.sleep(1)
        else:
            self.logger.error("[LIFT] ❌ 提升机非空闲状态")
            return False
        
        # 确认电梯到位后，清除到位状态
        if self.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
            self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
            self.logger.info(f"[LIFT] ✅ 清除电梯到位状态")
            time.sleep(3)
        else:
            self.logger.error("[LIFT] ❌ 电梯非到位状态")
            return False
        
        self.logger.info(f"[LIFT] 电梯到达 {self.get_lift()} 层")

        return True
            
    async def lift_move_by_layer(
            self,
            TASK_NO: int,
            LAYER: int
            ) -> bool:
        """[异步] 操作电梯移动。"""

        # 任务号检测
        lift_last_taskno = self.get_lift_last_taskno()
        if lift_last_taskno == TASK_NO:
            TASK_NO += 1
            self.logger.warning(f"[LIFT] 当前任务号和新任务号一致，调整任务号为 - {TASK_NO}")
        
        # 任务识别
        lift_running = self.read_bit(11, DB_11.RUNNING.value)
        lift_idle = self.read_bit(11, DB_11.IDLE.value)
        lift_no_cargo = self.read_bit(11, DB_11.NO_CARGO.value)
        lift_has_cargo = self.read_bit(11, DB_11.HAS_CARGO.value)
        lift_has_car = self.read_bit(11, DB_11.HAS_CAR.value)

        self.logger.info(f"[LIFT] 电梯状态 - 电梯运行中:{lift_running} 电梯是否空闲:{lift_idle} 电梯是否无货:{lift_no_cargo} 电梯是否有货:{lift_has_cargo} 电梯是否有车:{lift_has_car} ")

        if LAYER not in [1,2,3,4]:
            self.logger.error("[PLC] 楼层错误")
            return False
        
        else:
            if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
                
                self.logger.info("[LIFT] 电梯开始移动")
                self.lift_move(LIFT_TASK_TYPE.IDEL, TASK_NO, LAYER)
                
                self.logger.info("[LIFT] 电梯移动中...")
                await self.wait_for_bit_change(11, DB_11.RUNNING.value, 0)
                
                # 读取提升机是否空闲
                if self.read_bit(11, DB_11.IDLE.value):
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                # time.sleep(1)
                await asyncio.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                # time.sleep(1)
                await asyncio.sleep(3)
                self.logger.info(f"[LIFT] 电梯到达 {self.get_lift()} 层")
                
                return True
            
            elif lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==1:
                
                self.logger.info("[LIFT] 电梯开始移动")
                self.lift_move(LIFT_TASK_TYPE.CAR, TASK_NO, LAYER)
                
                self.logger.info("[LIFT] 电梯移动中...")
                await self.wait_for_bit_change(11, DB_11.RUNNING.value, 0)
                
                # 读取提升机是否空闲
                if self.read_bit(11, DB_11.IDLE.value):
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                # time.sleep(1)
                await asyncio.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                # time.sleep(1)
                await asyncio.sleep(3)
                self.logger.info(f"[LIFT] 电梯到达 {self.get_lift()} 层")
                
                return True

            elif lift_running==0 and lift_idle==1 and lift_no_cargo==0 and lift_has_cargo==1 and lift_has_car==0:
                
                self.logger.info("[LIFT] 电梯开始移动")
                self.lift_move(LIFT_TASK_TYPE.GOOD, TASK_NO, LAYER)
                
                self.logger.info("[LIFT] 电梯移动中...")
                await self.wait_for_bit_change(11, DB_11.RUNNING.value, 0)

                # 读取提升机是否空闲
                if self.read_bit(11, DB_11.IDLE.value):
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                # time.sleep(1)
                await asyncio.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                
                # time.sleep(1)
                await asyncio.sleep(3)
                self.logger.info(f"[LIFT] 电梯到达 {self.get_lift()} 层")
                
                return True
            
            else:
                await asyncio.sleep(3)
                self.logger.error(f"[LIFT] 未知状态，电梯到达 {self.get_lift()} 层")
                return False

    ########################################################
    ##################### 输送线相关函数 #####################
    ########################################################
    
    def inband_to_lift(self) -> bool:
        """输送线入库操作
        
        入库方向，从入口进入电梯。

        Returns:
            bool: 操作结果
        """

        # 放料完成（启动）
        self.write_bit(12, DB_12.FEED_COMPLETE_1010.value, 1)
        if self.read_bit(12, DB_12.FEED_COMPLETE_1010.value) == 1:
            self.write_bit(12, DB_12.FEED_COMPLETE_1010.value, 0)
        else:
            self.logger.error("[PLC] ❌ DB_12.FEED_COMPLETE_1010 清零失败")
            return False
    
        # 移动到提升机
        lift_code = struct.pack('!H', FLOOR_CODE.LIFT)
        self.write_db(12, DB_12.TARGET_1010.value, lift_code)
        time.sleep(1)
        if self.read_db(12, DB_12.TARGET_1010.value, 2) == lift_code:
            self.write_db(12, DB_12.TARGET_1010.value, b'\x00\x00')
            return True
        else:
            self.logger.error("[PLC] ❌ DB_12.TARGET_1010 清零失败")
            return False
    
    def lift_to_outband(self) -> bool:
        """输送线出库操作。
        
        出库方向，从电梯出来到出货口。

        Returns:
            bool: 操作结果
        """
        # 确认目标层到达
        self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
        time.sleep(0.5)
        
        # 写入出库指令
        data = struct.pack('!H', FLOOR_CODE.GATE)

        self.write_db(12, DB_12.TARGET_1020.value, data)
        time.sleep(1)
        if self.read_db(12, DB_12.TARGET_1020.value, 2) == data:
            self.write_db(12, DB_12.TARGET_1020.value, b'\x00\x00')
            self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
            return True
        else:
            self.logger.error("[PLC] ❌ DB_12.TARGET_1020 清零失败")
            self.logger.error("[PLC] ❌ DB_12.TARGET_LAYER_ARRIVED 清零失败")
            return False

    def floor_to_lift(self, floor_id: int) -> bool:
        """输送线出库操作。 !!! 现在这个函数弃用了 !!!
        
        出库方向，货物从楼层内的接驳位输送线进入电梯。

        !!! 注意 !!!
            使用前要先调用 feed_in_progress() 给一个放货进行中信号
            然后，穿梭车放货到楼层接驳位后，调用 feed_complete() 告诉 PLC 放货完成
            最后，使用 floor_to_lift() 启动输送线

        Args:
            floor_id: 楼层ID

        Returns:
            bool: 是否成功启动
        """

        # 楼层1
        if floor_id == 1:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, DB_12.TARGET_1030.value, data)
            time.sleep(1)
            if self.read_db(12, DB_12.TARGET_1030.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1030.value, b'\x00\x00')
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.TARGET_1030 清零失败")
                return False
                
        # 楼层2
        elif floor_id == 2:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, DB_12.TARGET_1040.value, data)
            time.sleep(1)
            if self.read_db(12, DB_12.TARGET_1040.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1040.value, b'\x00\x00')
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.TARGET_1040 清零失败")
                return False
        
        # 楼层3
        elif floor_id == 3:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, DB_12.TARGET_1050.value, data)
            time.sleep(1)
            if self.read_db(12, DB_12.TARGET_1050.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1050.value, b'\x00\x00')
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.TARGET_1050 清零失败")
                return False
            
        
        # 楼层4
        elif floor_id == 4:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, DB_12.TARGET_1060.value, data)
            time.sleep(1)
            if self.read_db(12, DB_12.TARGET_1060.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1060.value, b'\x00\x00')
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.TARGET_1060 清零失败")
                return False
        
        # 无效楼层
        else:
            self.logger.error(f"[PLC] ❌ {floor_id}无效的楼层")
            return False

    def lift_to_everylayer(self, floor_id: int) -> bool:
        """输送线入库操作。
        
        入库方向，货物从电梯内通过输送线，进入到楼层接驳位。

        Args:
            floor_id: 楼层ID，如1、2、3、4

        Returns:
            bool: 是否成功启动
        """
        # 确认目标层到达
        self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
        time.sleep(0.5)

        # 移动到1层
        if floor_id == 1:
            data = struct.pack('!H', FLOOR_CODE.LAYER_1)
            self.write_db(12, DB_12.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, DB_12.TARGET_1020.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1020.value, b'\x00\x00')
                time.sleep(1)
                self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.TARGET_1020 清零失败")
                self.logger.error("[PLC] ❌ DB_12.TARGET_LAYER_ARRIVED 清零失败")
                return False

        # 移动到2层
        elif floor_id == 2:
            data = struct.pack('!H', FLOOR_CODE.LAYER_2)
            self.write_db(12, DB_12.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, DB_12.TARGET_1020.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1020.value, b'\x00\x00')
                time.sleep(1)
                self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.TARGET_1020 清零失败")
                self.logger.error("[PLC] ❌ DB_12.TARGET_LAYER_ARRIVED 清零失败")
                return False
        
        # 移动到3层
        elif floor_id == 3:
            data = struct.pack('!H', FLOOR_CODE.LAYER_3)
            self.write_db(12, DB_12.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, DB_12.TARGET_1020.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1020.value, b'\x00\x00')
                time.sleep(1)
                self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.TARGET_1020 清零失败")
                self.logger.error("[PLC] ❌ DB_12.TARGET_LAYER_ARRIVED 清零失败")
                return False

        # 移动到4层
        elif floor_id == 4:
            data = struct.pack('!H', FLOOR_CODE.LAYER_4)
            self.write_db(12, DB_12.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, DB_12.TARGET_1020.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1020.value, b'\x00\x00')
                time.sleep(1)
                self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.TARGET_1020 清零失败")
                self.logger.error("[PLC] ❌ DB_12.TARGET_LAYER_ARRIVED 清零失败")
                return False

        # 无效楼层
        else:
            self.logger.error(f"[PLC] ❌ {floor_id} 无效的楼层")
            return False
        
    
    ########################################################
    ##################### 输送线标志位 #######################
    ########################################################
    
    def feed_in_process(self, floor_id: int) -> bool:
        """发送出库指令，放货进行中。
        
        出库方向，放货进行中指令，用于启动PLC输送线的标志位操作

        Args:
            floor_id: 楼层ID，如1、2、3、4

        Returns:
            bool: 是否成功启动
        """
        # 楼层1
        if floor_id == 1:
            self.write_bit(12, DB_12.FEED_IN_PROGRESS_1030.value, 1)
            return True
        # 楼层2
        elif floor_id == 2:
            self.write_bit(12, DB_12.FEED_IN_PROGRESS_1040.value, 1)
            return True
        # 楼层3
        elif floor_id == 3:
            self.write_bit(12, DB_12.FEED_IN_PROGRESS_1050.value, 1)
            return True
        # 楼层4
        elif floor_id == 4:
            self.write_bit(12, DB_12.FEED_IN_PROGRESS_1060.value, 1)
            return True
        # 无效楼层
        else:
            self.logger.error(f"[PLC] ❌ {floor_id} 无效的楼层")
            return False
        
    def feed_complete(self, floor_id: int) -> bool:
        """发送出库指令，放货完成，并且自动启动输送线。
        
        出库方向，货物从楼层内的接驳位输送线进入电梯
        
        !!! 注意 !!!
            使用前要调用 feed_in_progress() 给一个放货进行中的信号，唤醒输送线。
            然后，穿梭车移动货物到接驳位，移动完成后。
            最后，调用本函数，发送放货完成信号，此时输送线会启动，开始将货物移入电梯。
        
        Args:
            floor_id: 楼层ID，如1、2、3、4
        """

        # 楼层1
        if floor_id == 1:
            # 放料完成
            self.write_bit(12, DB_12.FEED_COMPLETE_1030.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.FEED_COMPLETE_1030.value) == 1:
                self.write_bit(12, DB_12.FEED_COMPLETE_1030.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.FEED_COMPLETE_1030 清零失败")
                return False

        # 楼层2
        elif floor_id == 2:
            # 放料完成
            self.write_bit(12, DB_12.FEED_COMPLETE_1040.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.FEED_COMPLETE_1040.value) == 1:
                self.write_bit(12, DB_12.FEED_COMPLETE_1040.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.FEED_COMPLETE_1040 清零失败")
                return False
        
        # 楼层3
        elif floor_id == 3:
            # 放料完成
            self.write_bit(12, DB_12.FEED_COMPLETE_1050.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.FEED_COMPLETE_1050.value) == 1:
                self.write_bit(12, DB_12.FEED_COMPLETE_1050.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.FEED_COMPLETE_1050 清零失败")
                return False
        
        # 楼层4
        elif floor_id == 4:
            # 放料完成
            self.write_bit(12, DB_12.FEED_COMPLETE_1060.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.FEED_COMPLETE_1060.value) == 1:
                self.write_bit(12, DB_12.FEED_COMPLETE_1060.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.FEED_COMPLETE_1060 清零失败")
                return False
        
        # 无效楼层
        else:
            self.logger.error(f"[PLC] ❌ {floor_id} 无效的楼层")
            return False
        
    def pick_in_process(self, floor_id: int) -> bool:
        """发送入库指令，取货进行中。
        
        入库方向，取货进行中指令，用于告知PLC穿梭车开始进行取货入库操作。
        
        Args:
            floor_id: 楼层ID，如1、2、3、4

        Returns:
            bool: 是否成功启动
        """
        # 楼层1
        if floor_id == 1:
            self.write_bit(12, DB_12.PICK_IN_PROGRESS_1030.value, 1)
            return True
        # 楼层2
        elif floor_id == 2:
            self.write_bit(12, DB_12.PICK_IN_PROGRESS_1040.value, 1)
            return True
        # 楼层3
        elif floor_id == 3:
            self.write_bit(12, DB_12.PICK_IN_PROGRESS_1050.value, 1)
            return True
        # 楼层4
        elif floor_id == 4:
            self.write_bit(12, DB_12.PICK_IN_PROGRESS_1060.value, 1)
            return True
        # 无效楼层
        else:
            self.logger.info(f"[PLC] ❌ {floor_id} 无效的楼层")
            return False
        
    def pick_complete(self, floor_id:int) -> bool:
        """发送入库指令，取货完成。
        
        入库方向，告知PLC穿梭车已将货物取走至库内。

        !!! 注意 !!! - 【不操作此步骤，PLC无法执行下一个任务，并且会闪烁报警。】
            使用前要调用 pick_in_progress() 给一个取货进行中的信号，告知PLC穿梭车取货进行中。
            然后，穿梭车移动货物到库内，移动完成后。
            最后，调用本函数，发送取货完成信号，此时输送线完成工作。
        
        Args:
            floor_id: 楼层ID，如1、2、3、4

        Returns:
            bool: 是否成功启动
        """
        # 楼层1
        if floor_id == 1:
            # 放料完成
            self.write_bit(12, DB_12.PICK_COMPLETE_1030.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.PICK_COMPLETE_1030.value) == 1:
                self.write_bit(12, DB_12.PICK_COMPLETE_1030.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.PICK_COMPLETE_1030 清零失败")
                return False

        # 楼层2
        elif floor_id == 2:
            # 放料完成
            self.write_bit(12, DB_12.PICK_COMPLETE_1040.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.PICK_COMPLETE_1040.value) == 1:
                self.write_bit(12, DB_12.PICK_COMPLETE_1040.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.PICK_COMPLETE_1040 清零失败")
                return False
        
        # 楼层3
        elif floor_id == 3:
            # 放料完成
            self.write_bit(12, DB_12.PICK_COMPLETE_1050.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.PICK_COMPLETE_1050.value) == 1:
                self.write_bit(12, DB_12.PICK_COMPLETE_1050.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.PICK_COMPLETE_1050 清零失败")
                return False
        
        # 楼层4
        elif floor_id == 4:
            # 放料完成
            self.write_bit(12, DB_12.PICK_COMPLETE_1060.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.PICK_COMPLETE_1060.value) == 1:
                self.write_bit(12, DB_12.PICK_COMPLETE_1060.value, 0)
                return True
            else:
                self.logger.error("[PLC] ❌ DB_12.PICK_COMPLETE_1060 清零失败")
                return False
        
        # 无效楼层
        else:
            self.logger.error(f"[PLC] {floor_id} 无效的楼层")
            return False
        
    
    ########################################################
    ##################### 扫码相机函数 #######################
    ########################################################
    
    def scan_qrcode(self) -> Union[bytes, bool]:
        """获取二维码。
        
        入库口输送线扫码相机控制。

        Returns:
            Union: 设备获取的二维码信息 or False
        """
        is_qrcode = self.read_db(11, DB_11.SCAN_CODE_RD.value, 2)
        self.logger.info(f"🙈 是否扫到码: {is_qrcode}")
        if is_qrcode == b'\x00\x01':
            qrcode = bytes()
            # for code_db_addr in range(24, 29):
            #     items = self.read_db(11, code_db_addr, 1)
            #     qrcode += items
            for code_db_addr in range(24, 44):
                items = self.read_db(11, code_db_addr, 1)
                if items != b'\x00':
                    qrcode += items
            return qrcode
        else:
            return False