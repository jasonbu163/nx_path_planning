# devices/plc_controller.py

import time
import struct

from .plc_connection_module import PLCConnectionBase
from .plc_enum import PLCAddress, FLOOR_CODE

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
        super().__init__(PLC_IP)

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

    def get_lift(self) -> int:
        """
        [获取电梯当前停在哪层]

        ::: return :::
            层数, 如 1层为 1
        """
        # 读取提升机所在层
        db = self.read_db(11, PLCAddress.CURRENT_LAYER.value, 2)
        # 返回解码的数据
        return struct.unpack('!H', db)[0]
        # 返回原数据
        # return db
    
    def life_move(self, TASK_TYPE, TASK_NUM, END_FLOOR) -> None:
        """
        [电梯操作] - 控制电梯到达目标楼层

        ::: param :::
            TASK_TYPE: 任务类型
            TASK_NUM: 任务号
            END_FLOOR: 目标层
        """
        task_type = struct.pack('!H', TASK_TYPE)
        task_num = struct.pack('!H', TASK_NUM)
        # start_floor = struct.pack('!H', start_floor)
        # start_floor = self.get_lift()
        end_floor = struct.pack('!H', END_FLOOR)

        # 任务类型
        self.write_db(12, PLCAddress.TASK_TYPE.value, task_type)
        # 任务号
        self.write_db(12, PLCAddress.TASK_NUMBER.value, task_num)
        # 起始层 起始位被电气部份屏蔽 可以不输入
        # self.write_db(12, PLCAddress.START_LAYER.value, start_floor)
        # 目标层
        self.write_db(12, PLCAddress.TARGET_LAYER.value, end_floor)
        
        # 读取提升机是否空闲
        if self.read_bit(11, PLCAddress.IDLE.value):
            self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

    ########################################################
    ##################### 输送线相关函数 #####################
    ########################################################
    
    def inband_to_lift(self) -> None:
        """
        [输送线操作] - 入库方向，从入口进入电梯
        """
        # 确认提升机已到1层
        self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

        # 放料完成（启动）
        self.write_bit(12, PLCAddress.FEED_COMPLETE_1010.value, 1)
        if self.read_bit(12, PLCAddress.FEED_COMPLETE_1010.value) == 1:
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1010.value, 0)

        # 移动到提升机
        lift_code = struct.pack('!H', FLOOR_CODE.LIFT)
        time.sleep(1)
        self.write_db(12, PLCAddress.TARGET_1010.value, lift_code)
        if self.read_db(12, PLCAddress.TARGET_1010.value, 2) == lift_code:
            self.write_db(12, PLCAddress.TARGET_1010.value, b'\x00\x00')
    
    
    def lift_to_outband(self) -> None:
        """
        [输送线操作] - 出库方向，从电梯出来到出货口
        """
        # 目标层到达
        self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)
        if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
            self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

        data = struct.pack('!H', FLOOR_CODE.GATE)
        self.write_db(12, PLCAddress.TARGET_1020.value, data)

    def floor_to_lift(self, FLOOR_ID: int) -> None:
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
            self.write_db(12, PLCAddress.TARGET_1030.value, data)
            if self.read_db(12, PLCAddress.TARGET_1030.value, 1) == data:
                self.write_db(12, PLCAddress.TARGET_1030.value, b'\x00\x00')

        # 楼层2
        elif FLOOR_ID == 2:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, PLCAddress.TARGET_1040.value, data)
            if self.read_db(12, PLCAddress.TARGET_1040.value, 1) == data:
                self.write_db(12, PLCAddress.TARGET_1040.value, b'\x00\x00')
        
        # 楼层3
        elif FLOOR_ID == 3:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, PLCAddress.TARGET_1050.value, data)
            if self.read_db(12, PLCAddress.TARGET_1050.value, 1) == data:
                self.write_db(12, PLCAddress.TARGET_1050.value, b'\x00\x00')
        
        # 楼层4
        elif FLOOR_ID == 4:
            # 货物送入提升机
            data = struct.pack('!H', FLOOR_CODE.LIFT)
            self.write_db(12, PLCAddress.TARGET_1060.value, data)
            if self.read_db(12, PLCAddress.TARGET_1060.value, 1) == data:
                self.write_db(12, PLCAddress.TARGET_1060.value, b'\x00\x00')
        
        # 无效楼层
        else:
            self.logger.warning("[PLC] 无效的楼层")
            raise ValueError("[PLC] Invalid target floor")
        

    def lift_to_everylayer(self, FLOOR_ID: int) -> None:
        """
        [输送线操作] - 入库方向，货物从电梯内通过输送线，进入到楼层接驳位

        ::: param :::
            FLOOR_ID: 楼层 int
        """

        # 确认目标层到达
        if self.read_bit(11, PLCAddress.RUNNING.value) == False and self.get_lift() == FLOOR_ID :
            time.sleep(1)
            self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

        time.sleep(0.5)
        # 移动到1层
        if FLOOR_ID == 1:
            data = struct.pack('!H', FLOOR_CODE.LAYER_1)
            self.write_db(12, PLCAddress.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
            # 到达目标层状态 清零
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
        
        # 移动到2层
        elif FLOOR_ID == 2:
            data = struct.pack('!H', FLOOR_CODE.LAYER_2)
            self.write_db(12, PLCAddress.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
            # 到达目标层状态 清零
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
        
        # 移动到3层
        elif FLOOR_ID == 3:
            data = struct.pack('!H', FLOOR_CODE.LAYER_3)
            self.write_db(12, PLCAddress.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
            # 到达目标层状态 清零
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

        # 移动到4层
        elif FLOOR_ID == 4:
            data = struct.pack('!H', FLOOR_CODE.LAYER_4)
            self.write_db(12, PLCAddress.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
            # 到达目标层状态 清零
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

        # 无效楼层
        else:
            self.logger.warning("[PLC] 无效的楼层")
            raise ValueError("[PLC] Invalid target floor")
        
    
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
            self.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1030.value, 1)
            return True
        # 楼层2
        elif FLOOR_ID == 2:
            self.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1040.value, 1)
            return True
        # 楼层3
        elif FLOOR_ID == 3:
            self.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1050.value, 1)
            return True
        # 楼层4
        elif FLOOR_ID == 4:
            self.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1060.value, 1)
            return True
        # 无效楼层
        else:
            self.logger.info("[PLC] 无效的楼层")
            return False
        
    def feed_complete(self, FLOOR_ID:int) -> None:
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
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 1)
            if self.read_bit(12, PLCAddress.FEED_COMPLETE_1030.value) == 1:
                self.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 0)

        # 楼层2
        elif FLOOR_ID == 2:
            # 放料完成
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1040.value, 1)
            if self.read_bit(12, PLCAddress.FEED_COMPLETE_1040.value) == 1:
                self.write_bit(12, PLCAddress.FEED_COMPLETE_1040.value, 0)
        
        # 楼层3
        elif FLOOR_ID == 3:
            # 放料完成
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1050.value, 1)
            if self.read_bit(12, PLCAddress.FEED_COMPLETE_1050.value) == 1:
                self.write_bit(12, PLCAddress.FEED_COMPLETE_1050.value, 0)
        
        # 楼层4
        elif FLOOR_ID == 4:
            # 放料完成
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1060.value, 1)
            if self.read_bit(12, PLCAddress.FEED_COMPLETE_1060.value) == 1:
                self.write_bit(12, PLCAddress.FEED_COMPLETE_1060.value, 0)
        
        # 无效楼层
        else:
            self.logger.warning("[PLC] 无效的楼层")
            raise ValueError("[PLC] Invalid target floor")
        
    def pick_in_process(self, FLOOR_ID: int) -> bool:
        """
        [取货进行中] - 入库方向，取货进行中指令，用于告知PLC穿梭车开始进行取货入库操作。
        
        ::: param :::
            FLOOR: 层数
        """
        # 楼层1
        if FLOOR_ID == 1:
            self.write_bit(12, PLCAddress.PICK_IN_PROGRESS_1030.value, 1)
            return True
        # 楼层2
        elif FLOOR_ID == 2:
            self.write_bit(12, PLCAddress.PICK_IN_PROGRESS_1040.value, 1)
            return True
        # 楼层3
        elif FLOOR_ID == 3:
            self.write_bit(12, PLCAddress.PICK_IN_PROGRESS_1050.value, 1)
            return True
        # 楼层4
        elif FLOOR_ID == 4:
            self.write_bit(12, PLCAddress.PICK_IN_PROGRESS_1060.value, 1)
            return True
        # 无效楼层
        else:
            self.logger.info("[PLC] 无效的楼层")
            return False
        
    def pick_complete(self, FLOOR_ID:int) -> None:
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
            self.write_bit(12, PLCAddress.PICK_COMPLETE_1030.value, 1)
            if self.read_bit(12, PLCAddress.PICK_COMPLETE_1030.value) == 1:
                self.write_bit(12, PLCAddress.PICK_COMPLETE_1030.value, 0)

        # 楼层2
        elif FLOOR_ID == 2:
            # 放料完成
            self.write_bit(12, PLCAddress.PICK_COMPLETE_1040.value, 1)
            if self.read_bit(12, PLCAddress.PICK_COMPLETE_1040.value) == 1:
                self.write_bit(12, PLCAddress.PICK_COMPLETE_1040.value, 0)
        
        # 楼层3
        elif FLOOR_ID == 3:
            # 放料完成
            self.write_bit(12, PLCAddress.PICK_COMPLETE_1050.value, 1)
            if self.read_bit(12, PLCAddress.PICK_COMPLETE_1050.value) == 1:
                self.write_bit(12, PLCAddress.PICK_COMPLETE_1050.value, 0)
        
        # 楼层4
        elif FLOOR_ID == 4:
            # 放料完成
            self.write_bit(12, PLCAddress.PICK_COMPLETE_1060.value, 1)
            if self.read_bit(12, PLCAddress.PICK_COMPLETE_1060.value) == 1:
                self.write_bit(12, PLCAddress.PICK_COMPLETE_1060.value, 0)
        
        # 无效楼层
        else:
            self.logger.warning("[PLC] 无效的楼层")
            raise ValueError("[PLC] Invalid target floor")