# devices/plc_controller.py
from plc_service import PLCService
from plc_service_asyncio import PLCService
from plc_enum import PLCAddress, TASK_TYPE, FLOOR
import time
import struct
import logging

class PLCController(PLCService):
    def __init__(self, plc_ip: str, car_ip: str):
        self.plc_ip = plc_ip
        self.client = PLCService(plc_ip)
        self.car_ip = car_ip
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def connect_plc(self):
        # 连接PLC（自动重试）
        while True:
            try:
                self.client.connect()
                if self.client.is_connected():
                    self.logger.info("✅ PLC 连接成功")
                    break
                else:
                    self.logger.warning("⚠️ PLC 连接失败，重试中...")
            except Exception as e:
                self.logger.error(f"❌ 连接PLC失败: {e}")
            time.sleep(1)

    # 二进制字符串转字节码
    def binary2bytes(self, binary_str):
        value = int(binary_str, 2)
        return struct.pack('!B', value)

    # 获得提升机所在层
    def get_lift(self):
        # 读取提升机所在层
        db = self.client.read_db(11, PLCAddress.CURRENT_LAYER.value, 2)
        # return struct.unpack('!H', db)[0]
        return db
    
    # 移动提升机
    def life_move(self, task_type, task_num, end_floor):
        task_type = struct.pack('!H', task_type)
        task_num = struct.pack('!H', task_num)
        # start_floor = struct.pack('!H', start_floor)
        start_floor = self.get_lift()
        end_floor = struct.pack('!H', end_floor)

        # 任务类型
        self.client.write_db(12, 0, task_type)
        # 任务号
        self.client.write_db(12, 6, task_num)
        # 起始层
        self.client.write_db(12, start=2, data=start_floor)
        # 目标层
        self.client.write_db(12, start=4, data=end_floor)
        # 读取提升机是否空闲
        if self.client.read_bit(11, PLCAddress.IDLE.value):
            self.client.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

    
    # 入库到提升机
    def inband(self):
        # 放料完成（启动）
        self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1010.value, 1)
        if self.client.read_bit(12, PLCAddress.FEED_COMPLETE_1010.value) == 1:
            self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1010.value, 0)

        # 移动到提升机
        lift_code = struct.pack('!H', FLOOR.LIFT)
        time.sleep(1)
        self.client.write_db(12, PLCAddress.TARGET_1010.value, lift_code)
        if self.client.read_db(12, PLCAddress.TARGET_1010.value, 2) == lift_code:
            self.client.write_db(12, PLCAddress.TARGET_1010.value, b'\x00\x00')
    
    # 从提升机出库
    def outband(self):
        # 目标层到达
        self.client.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)
        if self.client.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
            self.client.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

        data = struct.pack('!H', FLOOR.GATE)
        self.client.write_db(12, PLCAddress.TARGET_1020.value, data)

    # 楼层进入提升机
    def floor_to_lift(self, floor):
        """
        param floor: 楼层 int
        """
        # 楼层1
        if floor == 1:
            # 放料进行中
            self.client.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1030.value, 1)
            # 等待小车送货到提升机 -> 联动小车
            time.sleep(30)
            # 放料完成
            self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 1)
            if self.client.read_bit(12, PLCAddress.FEED_COMPLETE_1030.value) == 1:
                self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 0)
            # 货物送入提升机
            data = struct.pack('!H', FLOOR.LIFT)
            self.client.write_db(12, PLCAddress.TARGET_1030.value, data)
            if self.client.read_db(12, PLCAddress.TARGET_1030.value, 1) == data:
                self.client.write_db(12, PLCAddress.TARGET_1030.value, b'\x00\x00')

        # 楼层2
        elif floor == 2:
            # 放料进行中
            self.client.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1040.value, 1)
            # 等待小车送货到提升机 -> 联动小车
            time.sleep(30)
            # 放料完成
            self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1040.value, 1)
            if self.client.read_bit(12, PLCAddress.FEED_COMPLETE_1040.value) == 1:
                self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1040.value, 0)
            # 货物送入提升机
            data = struct.pack('!H', FLOOR.LIFT)
            self.client.write_db(12, PLCAddress.TARGET_1040.value, data)
            if self.client.read_db(12, PLCAddress.TARGET_1040.value, 1) == data:
                self.client.write_db(12, PLCAddress.TARGET_1040.value, b'\x00\x00')
        
        # 楼层3
        elif floor == 3:
            # 放料进行中
            self.client.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1050.value, 1)
            # 等待小车送货到提升机 -> 联动小车
            time.sleep(30)
            # 放料完成
            self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1050.value, 1)
            if self.client.read_bit(12, PLCAddress.FEED_COMPLETE_1050.value) == 1:
                self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1050.value, 0)
            # 货物送入提升机
            data = struct.pack('!H', FLOOR.LIFT)
            self.client.write_db(12, PLCAddress.TARGET_1050.value, data)
            if self.client.read_db(12, PLCAddress.TARGET_1050.value, 1) == data:
                self.client.write_db(12, PLCAddress.TARGET_1050.value, b'\x00\x00')
        
        # 楼层4
        elif floor == 4:
            # 放料进行中
            self.client.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1060.value, 1)
            # 等待小车送货到提升机 -> 联动小车
            time.sleep(30)
            # 放料完成
            self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1060.value, 1)
            if self.client.read_bit(12, PLCAddress.FEED_COMPLETE_1060.value) == 1:
                self.client.write_bit(12, PLCAddress.FEED_COMPLETE_1060.value, 0)
            # 货物送入提升机
            data = struct.pack('!H', FLOOR.LIFT)
            self.client.write_db(12, PLCAddress.TARGET_1060.value, data)
            if self.client.read_db(12, PLCAddress.TARGET_1060.value, 1) == data:
                self.client.write_db(12, PLCAddress.TARGET_1060.value, b'\x00\x00')
        
        else:
            print("无效的楼层")
        

    def lift_to_everylayer(self, target_floor):
        """
        :::param target_floor: 目标楼层
        """
        # 确认提升机
        print(f"确认提升机状态: {self.client.read_bit(11, PLCAddress.PLATFORM_PALLET_READY.value)}")

        # 确认目标层到达
        time.sleep(1)
        self.client.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

        time.sleep(1)
        # 移动到1层
        if target_floor == 1:
            data = struct.pack('!H', FLOOR.LAYER_1)
            self.client.write_db(12, PLCAddress.TARGET_1020.value, data)
            # 清零
            if self.client.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.client.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
        
        # 移动到2层
        elif target_floor == 2:
            data = struct.pack('!H', FLOOR.LAYER_2)
            self.client.write_db(12, PLCAddress.TARGET_1020.value, data)
            if self.client.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.client.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
        
        # 移动到3层
        elif target_floor == 3:
            data = struct.pack('!H', FLOOR.LAYER_3)
            self.client.write_db(12, PLCAddress.TARGET_1020.value, data)
            if self.client.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.client.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')

        # 移动到4层
        elif target_floor == 4:
            data = struct.pack('!H', FLOOR.LAYER_4)
            self.client.write_db(12, PLCAddress.TARGET_1020.value, data)
            if self.client.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.client.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')

        else:
            raise ValueError("Invalid target floor")

        # 到达目标层状态 清零
        if self.client.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
            self.client.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

    # 小车换层
    async def car_to_floor(self, traget_floor):
        # 获取小车坐标
        car_location = [1,1,1]
        car_current_floor = car_location[2]
        
        # 提升机到达小车所在层
        # 随机生成个3位整数整数任务号
        import random
        task_num = random.randint(100, 999)
        self.life_move(TASK_TYPE.IDEL, task_num, car_current_floor)

        # 小车 进入 提升机
        # 等待电梯到达楼层 读取电梯是否空闲
        await PLCService.wait_for_bit_change(self.client, 11, 13, 3, 1)
        # car_move(car_location, [6, 3, car_current_floor])
        
        # 提升机到达目标层
        task_num = random.randint(100, 999)
        self.life_move(TASK_TYPE.CAR, task_num, traget_floor)

        # 小车 离开 提升机
        # 等待电梯到达楼层 读取电梯是否空闲
        await PLCService.wait_for_bit_change(self.client, 11, 13, 3, 1)
        # 修改小车楼层
        # car_location_change([6, 3, traget_floor])
        # car_move([6, 3, traget_floor], [5, 3, target_floor])