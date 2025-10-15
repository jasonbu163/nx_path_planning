# tests/test_plc.py

# 配置路径
import os
import sys
from pathlib import Path
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))  # 添加项目根目录

# 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


from devices.plc_connection_module import PLCConnectionBase
from devices.plc_enum import DB_2, DB_5, DB_9, DB_11, DB_12, LIFT_TASK_TYPE
import time
import struct

# 移动提升机
def life_move(task_type, task_num, end_floor):
    task_type = struct.pack('!H', task_type)
    task_num = struct.pack('!H', task_num)
    # start_floor = struct.pack('!H', start_floor)
    start_floor = get_lift()
    end_floor = struct.pack('!H', end_floor)

    # 任务类型
    plc.write_db(12, 0, task_type)
    # 任务号
    plc.write_db(12, 6, task_num)
    # 起始层
    plc.write_db(12, start=2, data=start_floor)
    # 目标层
    plc.write_db(12, start=4, data=end_floor)
    # 读取提升机是否空闲
    if plc.read_bit(11, PLCAddress.IDLE.value):
        plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

def get_lift():
    # 读取提升机所在层
    db = plc.read_db(11, 14, 2)
    # return struct.unpack('!H', db)[0]
    return db

def lift_in():
    # 目标层到达
    data_str = '0010'
    data = binary2bytes(data_str)
    # print(data)
    plc.write_db(12, 24, data)
    if plc.read_db(12, 24, 1) == data:
        clean_data_str = '0000'
        clean_data = binary2bytes(clean_data_str)
        plc.write_db(12, 24, clean_data)

    data = 1030
    data = struct.pack('!H', data)
    plc.write_db(12, 12, data)

def lift_out():
    # 目标层到达
    data_str = '0010'
    data = binary2bytes(data_str)
    # print(data)
    plc.write_db(12, 24, data)
    if plc.read_db(12, 24, 1) == data:
        clean_data_str = '0000'
        clean_data = binary2bytes(clean_data_str)
        plc.write_db(12, 24, clean_data)

    data = 1030
    data = struct.pack('!H', data)
    plc.write_db(12, 12, data)

def floor_1_to_lift():
    # 放料进行中
    # data_str = '00000010'
    # data = binary2bytes(data_str)
    # print(data)
    # plc.write_db(12, 23, data)


    # 放料完成
    # data_str = '00000010'
    # data = binary2bytes(data_str)
    # print(data)
    # # plc.write_db(12, 22, data)
    # # print(plc.read_db(12, 22, 1))
    # 清零
    # if plc.read_db(12, 22, 1) == data:
    #     clean_data_str = '00000000'
    #     clean_data = binary2bytes(clean_data_str)
    #     # print(clean_data)
    #     plc.write_db(12, 22, clean_data)

    # 移动目标
    data = 1020
    data = struct.pack('!H', data)
    plc.write_db(12, 14, data)
    # 清零
    
def binary2bytes(binary_str):
    value = int(binary_str, 2)
    return struct.pack('!B', value)


def inband(plc):
    # 放料完成（启动）
    plc.write_bit(12, PLCAddress.FEED_COMPLETE_1010.value, 1)
    # 清零
    if plc.read_bit(12, PLCAddress.FEED_COMPLETE_1010.value) == 1:
        plc.write_bit(12, PLCAddress.FEED_COMPLETE_1010.value, 0)

    # 移动目标
    data = 1020
    data = struct.pack('!H', data)
    print(data)
    time.sleep(1)
    plc.write_db(12, PLCAddress.TARGET_1010.value, data)
    print(plc.read_db(12, PLCAddress.TARGET_1010.value, 2))
    # 清零
    if plc.read_db(12, PLCAddress.TARGET_1010.value, 2) == data:
        clean_data_str = 0
        clean_data = struct.pack('!H', clean_data_str)
        # print(clean_data)
        plc.write_db(12, PLCAddress.TARGET_1010.value, clean_data)

def lift_everwhere(plc, target, target_address):
    # 确认提升机
    print(f"确认提升机: {plc.read_bit(11, PLCAddress.PLATFORM_PALLET_READY_1020.value)}")

    # 确认目标层到达
    time.sleep(1)
    plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

    # 移动目标
    time.sleep(1)
    data = struct.pack('!H', target)
    print(data)
    plc.write_db(12, target_address, data)
    print(plc.read_db(12, target_address, 2))
    
    # 清零
    if plc.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
        clean_data = 0
        # print(clean_data)
        plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, clean_data)
    if plc.read_db(12, target_address, 2) == data:
        clean_data_str = 0
        clean_data = struct.pack('!H', clean_data_str)
        # print(clean_data)
        plc.write_db(12, target_address, clean_data)

def car_to_lift():
    # 放料进行中
    # data_str = '00000010'
    # data = binary2bytes(data_str)
    # print(data)
    # plc.write_db(12, 23, data)

    # 放料完成
    # data_str = '00000010'
    # data = binary2bytes(data_str)
    # print(data)
    # # plc.write_db(12, 22, data)
    # # print(plc.read_db(12, 22, 1))
    # 清零
    # if plc.read_db(12, 22, 1) == data:
    #     clean_data_str = '00000000'
    #     clean_data = binary2bytes(clean_data_str)
    #     # print(clean_data)
    #     plc.write_db(12, 22, clean_data)

    # 移动目标
    data = 1020
    data = struct.pack('!H', data)
    plc.write_db(12, 14, data)
    # 清零

def test_connect():
    plc = PLCConnectionBase("192.168.8.10")

    # 连接PLC（自动重试）
    while True:
        try:
            plc.connect()
            if plc.is_connected():
                logger.info("✅ PLC 连接成功")
                break
            else:
                logger.warning("⚠️ PLC 连接失败，重试中...")
        except Exception as e:
            logger.error(f"❌ 连接PLC失败: {e}")
        time.sleep(1)
    
    plc.disconnect()

def test_inband(plc):
    try:
        ############ 入库 ###############
        task_num = 1
        task_layer = [3,3,1]
        car_location = [3,2,4]
        
        # # step1: 确认小车是否在目标层
        # if car_location[4] != task_layer[2]:
        #     # 移车任务
        #     car_task_num = 1
        #     life_move(TASK_TYPE.IDEL, car_task_num+1, end_floor=car_location[2])
        #     # 确认电梯到位
        #     if plc.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
        #         plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
        #     # 小车进电梯
        #     car_
        #     car_move(car_location, )
        
        # car_task_num = 11
        # life_move(TASK_TYPE.IDEL, car_task_num, end_floor=1)
        # # 确认电梯到位
        # if plc.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
        #     plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

        # step: 入货口进入电梯
        # inband(plc)
        # time.sleep(13)

        # # step: 电梯到达货物层
        # good_task_num = 34
        # life_move(TASK_TYPE.GOOD, good_task_num, end_floor=2)
        # # 确认电梯到位
        # if plc.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
        #     plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

        # time.sleep(20)
        # lift_everwhere(plc, 1040, PLCAddress.TARGET_1020.value)

        # 1040的取料进行中会自动清零，给一下信号即可
        plc.write_bit(12, PLCAddress.PICK_IN_PROGRESS_1040.value, 1)

        # 1030的放料完成信号给完要手动清零。
        # 这里是小车取货
        time.sleep(15)
        
        # 取料完成
        plc.write_bit(12, PLCAddress.PICK_COMPLETE_1040.value, 1)
        if plc.read_bit(12, PLCAddress.PICK_COMPLETE_1040.value):
            plc.write_bit(12, PLCAddress.PICK_COMPLETE_1040.value, 0)

        logger.info("📤 写入成功")
    except Exception as e:
        logger.error(f"❌ 写入失败: {e}")

def test_outband(plc):
    try:
        ############ 出库 ###############
        # task_num = 1
        # task_layer = [3,3,1]
        # print(task_layer[2])
        
        # step1: 电梯先到货物所在楼层
        # life_move(TASK_TYPE.IDEL, task_num, end_floor=task_layer[2])
        
        # step2: 车把货物送到出库传送带
        # 先给放料进行中
        # plc.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1030.value, 1)
        # good_out(task_num)
        # if good_out():
        # time.sleep(20) # 模拟小车事件
        
        # step3: 放料
        # 放料完成
        # plc.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 1)
        # if plc.read_bit(12, PLCAddress.FEED_COMPLETE_1030.value) == 1:
        #     plc.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 0)
        
        # step4: 进入电梯
        # data_1020 = struct.pack("!H", 1020)
        # # plc.write_db(12, PLCAddress.TARGET_1030.value, data_1020)
        # if plc.read_db(12, PLCAddress.TARGET_1030.value, 2) == data_1020:
        #     data_clean = struct.pack("!H", 0)
        #     plc.write_db(12, PLCAddress.TARGET_1030.value, data_clean)

        # step5: 将电梯移动到1楼
        # time.sleep(3)
        # if plc.read_bit(11, PLCAddress.PLATFORM_PALLET_READY.value) == 1:
        #     life_move(TASK_TYPE.GOOD, task_num, end_floor=1)
        # 确认电梯到位
        # if plc.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
        #     plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
        
        # step6: 将货物移出电梯
        # lift_everwhere(plc, 1010, PLCAddress.TARGET_1020.value)

        logger.info("📤 写入成功")
    except Exception as e:
        logger.error(f"❌ 写入失败: {e}")

def test_1(plc):
    try:
        # plc.write_db(11, 0, b'\x01\x02\x03')
        # task_num = 11
        # life_move(TASK_TYPE.IDEL, task_num, end_floor=1)
        # floor_1_in()

        # data = plc.read_db(12, 24, 1)
        # print(data)
        
        # lift_in()
        # floor_1_to_lift()

        logger.info("📤 写入成功")
    except Exception as e:
        logger.error(f"❌ 写入失败: {e}")

def main():
    PLC_IP = "192.168.8.10"
    plc = PLCConnectionBase(PLC_IP)
    
    plc.connect()

    test_1(plc)
    
    plc.disconnect()

if __name__ == "__main__":
    main()