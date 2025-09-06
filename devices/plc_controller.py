# devices/plc_controller.py

import time
import struct
from typing import Union
import asyncio

from .plc_connection_module import PLCConnectionBase
from .plc_enum import DB_2, DB_9, DB_11, DB_12, FLOOR_CODE, LIFT_TASK_TYPE

class PLCController(PLCConnectionBase):
    """
    [PLC - 高级操作类]
    """
    
    def __init__(self, PLC_IP: str):
        """
        [初始化PLC客户端]

        ::: param :::
            PLC_IP: plc地址, 如 “192.168.3.10”
        """
        self._plc_ip = PLC_IP
        super().__init__(self._plc_ip)

    # 二进制字符串转字节码
    def binary2bytes(self, BINARY_STR) -> bytes:
        """
        [二进制字符串转字节码]

        ::: param :::
            binary_str: 二进制字符串

        ::: return :::
            字节码
        """
        value = int(BINARY_STR, 2)
        return struct.pack('!B', value)

    ########################################################
    ##################### 电梯相关函数 #######################
    ########################################################

    def plc_checker(self) -> bool:
        """
        [PLC校验器] - 在plc连接成功之后，必须使用plc_checker进行校验，否则会导致设备安全事故
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
            self.logger.info("✅ PLC就绪")
            return True
        else:
            self.logger.error("❌ PLC错误，请检查设备状态")
            return False
    
    def get_lift(self) -> int:
        """
        [获取电梯当前停在哪层] - 无连接PLC

        ::: return :::
            层数, 如 1层为 1
        """
        # 读取提升机所在层
        db = self.read_db(11, DB_11.CURRENT_LAYER.value, 2)
        # 返回解码的数据
        return struct.unpack('!H', db)[0]
        # 返回原数据
        # return db
    

    def get_lift_last_taskno(self) -> int:
        """
        [获取电梯上一次任务号] - 无连接PLC

        ::: return :::
            层数, 如 1层为 1
        """
        # 读取提升机所在层
        db = self.read_db(9, DB_9.LAST_TASK_NO.value, 2)
        # 返回解码的数据
        return struct.unpack('!H', db)[0]
        # 返回原数据
        # return db
    

    def lift_move(
            self,
            TASK_TYPE: int,
            TASK_NO: int,
            END_FLOOR: int
            ) -> None:
        """
        [电梯操作] - 控制电梯到达目标楼层 - 无连接PLC

        ::: param :::
            TASK_TYPE: 任务类型
            TASK_NO: 任务号
            END_FLOOR: 目标层
        """

        # 任务号检测
        lift_last_taskno = self.get_lift_last_taskno()
        if lift_last_taskno == TASK_NO:
            TASK_NO += 1
            self.logger.warning(f"[LIFT] 当前任务号和新任务号一致，调整任务号为 - {TASK_NO}")
        
        task_type = struct.pack('!H', TASK_TYPE)
        task_num = struct.pack('!H', TASK_NO)
        # start_floor = struct.pack('!H', start_floor)
        # start_floor = self.get_lift()
        end_floor = struct.pack('!H', END_FLOOR)

        # 任务类型
        self.write_db(12, DB_12.TASK_TYPE.value, task_type)
        # 任务号
        self.write_db(12, DB_12.TASK_NUMBER.value, task_num)
        # 起始层 起始位被电气部份屏蔽 可以不输入
        # self.write_db(12, PLCAddress.START_LAYER.value, start_floor)
        # 目标层
        self.write_db(12, DB_12.TARGET_LAYER.value, end_floor)
        

    def _lift_move_by_layer(
            self,
            TASK_NO: int,
            LAYER: int
            ) -> bool:
        """
        [同步 - 移动电梯] - 带PLC连接
        """

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
                self.wait_for_bit_change_sync(11, DB_11.RUNNING.value, 0)
                
                # 读取提升机是否空闲
                if self.read_bit(11, DB_11.IDLE.value):
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                time.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                time.sleep(1)
                self.logger.info(f"[LIFT] 电梯到达 {self.get_lift()} 层")
                
                return True
            
            elif lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==1:
                
                self.logger.info("[LIFT] 电梯开始移动")
                self.lift_move(LIFT_TASK_TYPE.CAR, TASK_NO, LAYER)
                
                self.logger.info("[LIFT] 电梯移动中...")
                self.wait_for_bit_change_sync(11, DB_11.RUNNING.value, 0)
                
                # 读取提升机是否空闲
                if self.read_bit(11, DB_11.IDLE.value):
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                time.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                time.sleep(1)
                self.logger.info(f"[LIFT] 电梯到达 {self.get_lift()} 层")
                
                return True

            elif lift_running==0 and lift_idle==1 and lift_no_cargo==0 and lift_has_cargo==1 and lift_has_car==0:
                
                self.logger.info("[LIFT] 电梯开始移动")
                self.lift_move(LIFT_TASK_TYPE.GOOD, TASK_NO, LAYER)
                
                self.logger.info("[LIFT] 电梯移动中...")
                self.wait_for_bit_change_sync(11, DB_11.RUNNING.value, 0)

                # 读取提升机是否空闲
                if self.read_bit(11, DB_11.IDLE.value):
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
                time.sleep(1)
                # 确认电梯到位后，清除到位状态
                if self.read_bit(12, DB_12.TARGET_LAYER_ARRIVED.value) == 1:
                    self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 0)
                
                time.sleep(1)
                self.logger.info(f"[LIFT] 电梯到达 {self.get_lift()} 层")
                
                return True
            
            else:
                self.logger.error("[LIFT] 未知状态")
                return False
            
    async def lift_move_by_layer(
            self,
            TASK_NO: int,
            LAYER: int
            ) -> bool:
        """
        [异步 - 移动电梯] - 带PLC连接
        """

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
                await asyncio.sleep(1)
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
                await asyncio.sleep(1)
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
                await asyncio.sleep(1)
                self.logger.info(f"[LIFT] 电梯到达 {self.get_lift()} 层")
                
                return True
            
            else:
                self.logger.error("[LIFT] 未知状态")
                return False

    ########################################################
    ##################### 输送线相关函数 #####################
    ########################################################
    
    def inband_to_lift(self) -> bool:
        """
        [输送线操作] - 入库方向，从入口进入电梯
        """

        # 放料完成（启动）
        self.write_bit(12, DB_12.FEED_COMPLETE_1010.value, 1)
        if self.read_bit(12, DB_12.FEED_COMPLETE_1010.value) == 1:
            self.write_bit(12, DB_12.FEED_COMPLETE_1010.value, 0)
        else:
            self.logger.error("清零失败")
            return False
    
        # 移动到提升机
        lift_code = struct.pack('!H', FLOOR_CODE.LIFT)
        self.write_db(12, DB_12.TARGET_1010.value, lift_code)
        time.sleep(1)
        if self.read_db(12, DB_12.TARGET_1010.value, 2) == lift_code:
            self.write_db(12, DB_12.TARGET_1010.value, b'\x00\x00')
            return True
        else:
            self.logger.error("清零失败")
            return False
        
    
    
    def lift_to_outband(self) -> bool:
        """
        [输送线操作] - 出库方向，从电梯出来到出货口
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
            self.logger.error("清零失败")
            return False
            


    def floor_to_lift(self, FLOOR_ID: int) -> bool:
        """
        !!! 现在这个函数弃用了 !!!

        [输送线操作] - 出库方向，货物从楼层内的接驳位输送线进入电梯

        !!! 注意 !!!
            使用前要先调用 feed_in_progress() 给一个放货进行中信号
            然后，穿梭车放货到楼层接驳位后，调用 feed_complete() 告诉 PLC 放货完成
            最后，使用 floor_to_lift() 启动输送线

        ::: param :::
            FLOOR_ID: 楼层 int
        """

        # 楼层1
        if FLOOR_ID == 1:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, DB_12.TARGET_1030.value, data)
            time.sleep(1)
            if self.read_db(12, DB_12.TARGET_1030.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1030.value, b'\x00\x00')
                return True
            else:
                self.logger.error("清零失败")
                return False
                

        # 楼层2
        elif FLOOR_ID == 2:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, DB_12.TARGET_1040.value, data)
            time.sleep(1)
            if self.read_db(12, DB_12.TARGET_1040.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1040.value, b'\x00\x00')
                return True
            else:
                self.logger.error("清零失败")
                return False
        
        # 楼层3
        elif FLOOR_ID == 3:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, DB_12.TARGET_1050.value, data)
            time.sleep(1)
            if self.read_db(12, DB_12.TARGET_1050.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1050.value, b'\x00\x00')
                return True
            else:
                self.logger.error("清零失败")
                return False
            
        
        # 楼层4
        elif FLOOR_ID == 4:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, DB_12.TARGET_1060.value, data)
            time.sleep(1)
            if self.read_db(12, DB_12.TARGET_1060.value, 2) == data:
                self.write_db(12, DB_12.TARGET_1060.value, b'\x00\x00')
                return True
            else:
                self.logger.error("清零失败")
                return False
        
        # 无效楼层
        else:
            self.logger.warning("[PLC] 无效的楼层")
            return False
        

    def lift_to_everylayer(self, FLOOR_ID: int) -> bool:
        """
        [输送线操作] - 入库方向，货物从电梯内通过输送线，进入到楼层接驳位

        ::: param :::
            FLOOR_ID: 楼层 int
        """
        # 确认目标层到达
        self.write_bit(12, DB_12.TARGET_LAYER_ARRIVED.value, 1)
        time.sleep(0.5)

        # 移动到1层
        if FLOOR_ID == 1:
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
                self.logger.error("清零失败")
                return False

        
        # 移动到2层
        elif FLOOR_ID == 2:
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
                self.logger.error("清零失败")
                return False
        
        # 移动到3层
        elif FLOOR_ID == 3:
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
                self.logger.error("清零失败")
                return False

        # 移动到4层
        elif FLOOR_ID == 4:
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
                self.logger.error("清零失败")
                return False

        # 无效楼层
        else:
            self.logger.warning("[PLC] 无效的楼层")
            return False
        
    
    ########################################################
    ##################### 输送线标志位 #######################
    ########################################################
    
    def feed_in_process(self, FLOOR_ID: int) -> bool:
        """
        [放货进行中] - 出库方向，放货进行中指令，用于启动PLC输送线的标志位操作

        ::: param :::
            FLOOR: 层数
        """
        # 楼层1
        if FLOOR_ID == 1:
            self.write_bit(12, DB_12.FEED_IN_PROGRESS_1030.value, 1)
            return True
        # 楼层2
        elif FLOOR_ID == 2:
            self.write_bit(12, DB_12.FEED_IN_PROGRESS_1040.value, 1)
            return True
        # 楼层3
        elif FLOOR_ID == 3:
            self.write_bit(12, DB_12.FEED_IN_PROGRESS_1050.value, 1)
            return True
        # 楼层4
        elif FLOOR_ID == 4:
            self.write_bit(12, DB_12.FEED_IN_PROGRESS_1060.value, 1)
            return True
        # 无效楼层
        else:
            self.logger.info("[PLC] 无效的楼层")
            return False
        
    def feed_complete(self, FLOOR_ID:int) -> bool:
        """
        [放货完成] & [输送线操作] - 出库方向，货物从楼层内的接驳位输送线进入电梯
        
        !!! 注意 !!!
            使用前要调用 feed_in_progress() 给一个放货进行中的信号，唤醒输送线。
            然后，穿梭车移动货物到接驳位，移动完成后。
            最后，调用本函数，发送放货完成信号，此时输送线会启动，开始将货物移入电梯。
        
        ::: param :::
            FLOOR_ID: 楼层 int
        """

        # 楼层1
        if FLOOR_ID == 1:
            # 放料完成
            self.write_bit(12, DB_12.FEED_COMPLETE_1030.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.FEED_COMPLETE_1030.value) == 1:
                self.write_bit(12, DB_12.FEED_COMPLETE_1030.value, 0)
                return True
            else:
                self.logger.error("清零失败")
                return False

        # 楼层2
        elif FLOOR_ID == 2:
            # 放料完成
            self.write_bit(12, DB_12.FEED_COMPLETE_1040.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.FEED_COMPLETE_1040.value) == 1:
                self.write_bit(12, DB_12.FEED_COMPLETE_1040.value, 0)
                return True
            else:
                self.logger.error("清零失败")
                return False
        
        # 楼层3
        elif FLOOR_ID == 3:
            # 放料完成
            self.write_bit(12, DB_12.FEED_COMPLETE_1050.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.FEED_COMPLETE_1050.value) == 1:
                self.write_bit(12, DB_12.FEED_COMPLETE_1050.value, 0)
                return True
            else:
                self.logger.error("清零失败")
                return False
        
        # 楼层4
        elif FLOOR_ID == 4:
            # 放料完成
            self.write_bit(12, DB_12.FEED_COMPLETE_1060.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.FEED_COMPLETE_1060.value) == 1:
                self.write_bit(12, DB_12.FEED_COMPLETE_1060.value, 0)
                return True
            else:
                self.logger.error("清零失败")
                return False
        # 无效楼层
        else:
            self.logger.warning("[PLC] 无效的楼层")
            return False
        
    def pick_in_process(self, FLOOR_ID: int) -> bool:
        """
        [取货进行中] - 入库方向，取货进行中指令，用于告知PLC穿梭车开始进行取货入库操作。
        
        ::: param :::
            FLOOR: 层数
        """
        # 楼层1
        if FLOOR_ID == 1:
            self.write_bit(12, DB_12.PICK_IN_PROGRESS_1030.value, 1)
            return True
        # 楼层2
        elif FLOOR_ID == 2:
            self.write_bit(12, DB_12.PICK_IN_PROGRESS_1040.value, 1)
            return True
        # 楼层3
        elif FLOOR_ID == 3:
            self.write_bit(12, DB_12.PICK_IN_PROGRESS_1050.value, 1)
            return True
        # 楼层4
        elif FLOOR_ID == 4:
            self.write_bit(12, DB_12.PICK_IN_PROGRESS_1060.value, 1)
            return True
        # 无效楼层
        else:
            self.logger.info("[PLC] 无效的楼层")
            return False
        
    def pick_complete(self, FLOOR_ID:int) -> bool:
        """
        [取货完成] - 入库方向，告知PLC穿梭车已将货物取走至库内

        !!! 注意 !!! - 【不操作此步骤，PLC无法执行下一个任务，并且会闪烁报警。】
            使用前要调用 pick_in_progress() 给一个取货进行中的信号，告知PLC穿梭车取货进行中。
            然后，穿梭车移动货物到库内，移动完成后。
            最后，调用本函数，发送取货完成信号，此时输送线完成工作。
        
        ::: param :::
            FLOOR_ID: 楼层 int
        """
        # 楼层1
        if FLOOR_ID == 1:
            # 放料完成
            self.write_bit(12, DB_12.PICK_COMPLETE_1030.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.PICK_COMPLETE_1030.value) == 1:
                self.write_bit(12, DB_12.PICK_COMPLETE_1030.value, 0)
                return True
            else:
                self.logger.error("清零失败")
                return False

        # 楼层2
        elif FLOOR_ID == 2:
            # 放料完成
            self.write_bit(12, DB_12.PICK_COMPLETE_1040.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.PICK_COMPLETE_1040.value) == 1:
                self.write_bit(12, DB_12.PICK_COMPLETE_1040.value, 0)
                return True
            else:
                self.logger.error("清零失败")
                return False
        
        # 楼层3
        elif FLOOR_ID == 3:
            # 放料完成
            self.write_bit(12, DB_12.PICK_COMPLETE_1050.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.PICK_COMPLETE_1050.value) == 1:
                self.write_bit(12, DB_12.PICK_COMPLETE_1050.value, 0)
                return True
            else:
                self.logger.error("清零失败")
                return False
        
        # 楼层4
        elif FLOOR_ID == 4:
            # 放料完成
            self.write_bit(12, DB_12.PICK_COMPLETE_1060.value, 1)
            time.sleep(1)
            if self.read_bit(12, DB_12.PICK_COMPLETE_1060.value) == 1:
                self.write_bit(12, DB_12.PICK_COMPLETE_1060.value, 0)
                return True
            else:
                self.logger.error("清零失败")
                return False
        
        # 无效楼层
        else:
            self.logger.error("[PLC] 无效的楼层")
            return False
        
    
    ########################################################
    ##################### 扫码相机函数 #######################
    ########################################################
    
    def scan_qrcode(self) -> Union[bytes, bool]:
        """
        [获取二维码] - 入库口输送线扫码相机控制

        ::: return :::
            qrcode: 设备获取的二维码信息
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