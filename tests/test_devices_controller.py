# tests/test_devices_controller.py

import sys_path
sys_path.setup_path()

import asyncio
import time

import config
from devices.devices_controller import DevicesController
from devices.plc_controller import PLCController
from devices.car_controller import CarController
from devices.plc_enum import LIFT_TASK_TYPE, DB_12, DB_11

def test_plc_controller(PLC_IP):
    """测试PLC控制器"""
    plc = PLCController(PLC_IP)
    plc.connect()
    
    scan_msg = plc.scan_qrcode()
    plc.logger.info(f"🙈 扫码内容: {scan_msg}")
    
    if scan_msg == b'A0007':
        plc.logger.info("🚧 开始入库")
        plc.inband_to_lift()
        plc.logger.info("🚧 入库中...")
        plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
        plc.logger.info("✅ 入库完成")
    else:
        plc.logger.error("❌ 托盘识别错误，请检查托盘是否扫到二维码。")
        plc.disconnect()
        return False
    
    plc.logger.info("🚧 电梯开始移动")
    plc.lift_move(LIFT_TASK_TYPE.GOOD, 1, 2)
    plc.logger.info("🚧 电梯移动中...")
    plc.wait_for_bit_change_sync(11, DB_11.RUNNING.value, 0)
    plc.logger.info("🚧 电梯到达")

    time.sleep(2)

    plc.logger.info("🚧 电梯开始移动")
    plc.lift_move(LIFT_TASK_TYPE.GOOD, 2, 1)
    plc.logger.info("🚧 电梯移动中...")
    plc.wait_for_bit_change_sync(11, DB_11.RUNNING.value, 0)
    plc.logger.info("🚧 电梯到达")

    plc.logger.info("🚧 开始出库")
    plc.lift_to_outband()
    plc.logger.info("🚧 出库中...")
    plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)
    plc.logger.info("✅ 出库完成")


    plc.disconnect()

def test_car_controller(CAR_IP, CAR_PORT):
    """测试车辆控制器"""
    car = CarController(CAR_IP, CAR_PORT)

    car.send_heartbeat()
    power_msg = car.car_power()
    car.logger.info(f"🔋 车辆电量: {power_msg}")

    car.logger.info("🚗 车辆开始移动")
    task_no = 12
    car_target = '1,4,1'
    car.car_move(task_no, car_target)
    car.logger.info("⌛️ 车辆移动中...")
    car.wait_car_move_complete_by_location_sync(car_target)
    car.logger.info("✅ 车辆已到达目标位置")

def test_devices_controller(PLC_IP, CAR_IP, CAR_PORT):
    
    # 创建设备控制器
    d_c = DevicesController(PLC_IP, CAR_IP, CAR_PORT)
    
    # 开启PlC连接
    d_c.plc.connect()

    # 开始测试
    d_c.car_cross_layer(TASK_NO=1, TARGET_LAYER=2)
    # d_c.task_inband(TASK_NO=2, TARGET_LOCATION="1,1,2")
    # d_c.task_outband(TASK_NO=3, TARGET_LOCATION="1,1,2")
    
    # 关闭PlC连接
    d_c.plc.disconnect()

async def main():
    plc_ip = config.PLC_IP
    car_ip = config.CAR_IP
    car_port = config.CAR_PORT

    # 开始测试时间
    start_time = time.time()

    test_plc_controller(plc_ip)
    # test_car_controller(car_ip, car_port)
    # test_devices_controller(plc_ip, car_ip, car_port)
    
    # 程序用时
    espect_time = time.time() - start_time
    print(f"✅ 测试完成，耗时{espect_time:.2f}秒")


if __name__ == "__main__":
    asyncio.run(main())