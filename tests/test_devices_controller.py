# tests/test_devices_controller.py

import sys_path
sys_path.setup_path()

import asyncio
import time
import random

import app.core.config as config
from app.devices.devices_controller import DevicesController
from app.plc_system.controller import PLCController
from app.res_system.controller.controller_base import CarController
from app.plc_system.enum import LIFT_TASK_TYPE, DB_12, DB_11, DB_2

def test_plc_controller(plc_ip: str):
    """测试PLC控制器"""

    plc = PLCController(plc_ip)
    
    if plc.connect():
        plc.logger.info(f"[PLC] ✅ {plc_ip} 连接成功")
    else:
        plc.disconnect()
        plc.logger.error(f"[PLC] ❌ {plc_ip} 连接失败")
        return False

    current_floor = plc.get_lift()
    plc.logger.info(f"电梯在 {current_floor} 楼")
    
    # scan_msg = plc.scan_qrcode()
    # plc.logger.info(f"🙈 扫码内容: {scan_msg}")
    
    # if scan_msg == b'A0007':
    #     plc.logger.info("🚧 开始入库")
    #     plc.inband_to_lift()
    #     plc.logger.info("🚧 入库中...")
    #     plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
    #     plc.logger.info("✅ 入库完成")
    # else:
    #     plc.disconnect()
    #     plc.logger.error("❌ 托盘识别错误，请检查托盘是否扫到二维码。")
    #     return False
    
    task_no = random.randint(1, 100)
    target_floor = 2

    if current_floor != target_floor:

        if plc.plc_checker():
            plc.logger.info("🚧 电梯开始移动...")

            if plc.lift_move_by_layer_sync(task_no, target_floor):
                plc.logger.info("✅ 电梯工作指令发送成功")
            else:
                plc.disconnect()
                plc.logger.error(f"❌ 电梯工作指令发送失败")
                return False
            
            plc.logger.info(f"⌛️ 等待电梯到达{target_floor}层")

            if plc.wait_lift_move_complete_by_location_sync():
                plc.logger.info(f"✅ 电梯已到达{target_floor}层") 
            else:
                plc.disconnect()
                plc.logger.error(f"❌ 电梯未到达{target_floor}层")
                return False
            
        else:
            plc.disconnect()
            plc.logger.error("❌ PLC错误")
            return False

    time.sleep(2)

    task_no += 1
    target_floor = 1

    if plc.plc_checker():
    
        plc.logger.info("🚧 电梯开始移动...")
        if plc.lift_move_by_layer_sync(task_no, target_floor):
            plc.logger.info("✅ 电梯工作指令发送成功")
        else:
            plc.disconnect()
            plc.logger.error(f"❌ 电梯工作指令发送失败")
            return False
        
        plc.logger.info(f"⌛️ 等待电梯到达{target_floor}层")

        if plc.wait_lift_move_complete_by_location_sync():
            plc.logger.info(f"✅ 电梯已到达{target_floor}层")
        else:
            plc.disconnect()
            plc.logger.error(f"❌ 电梯未到达{target_floor}层")
            return False
    else:
        plc.disconnect()
        plc.logger.error("❌ PLC错误")
        return False

    # plc.logger.info("🚧 开始出库")
    # plc.lift_to_outband()
    # plc.logger.info("🚧 出库中...")
    # plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)
    # plc.logger.info("✅ 出库完成")

    plc.disconnect()

def test_car_controller(CAR_IP, CAR_PORT):
    """测试车辆控制器"""
    car = CarController(CAR_IP, CAR_PORT)

    car.send_heartbeat()
    power_msg = car.car_power()
    car.logger.info(f"🔋 车辆电量: {power_msg}")
    loc_msg = car.car_current_location()
    car.logger.info(f"🚗 车辆位置: {loc_msg}")

    car.logger.info("🚗 车辆开始移动")
    task_no = random.randint(1, 100)
    car_target = '3,3,1'
    car.car_move(task_no, car_target)
    car.logger.info("⌛️ 车辆移动中...")
    car.wait_car_move_complete_by_location_sync(car_target)
    car.logger.info("✅ 车辆已到达目标位置")

def test_devices_controller(plc_ip, car_ip, car_port):
    # 创建设备控制器
    d_c = DevicesController(plc_ip, car_ip, car_port)

    # 开始测试
    # d_c.car_cross_layer(task_no=1, target_layer=1)
    # d_c.task_inband(task_no=2, target_location="5,1,2")
    d_c.task_outband(task_no=3, target_location="5,4,1")
    
def main():
    plc_ip = config.PLC_IP
    car_ip = config.CAR_IP
    car_port = config.CAR_PORT

    # 开始测试时间
    start_time = time.time()

    # test_plc_controller(plc_ip)
    # test_car_controller(car_ip, car_port)
    # test_devices_controller(plc_ip, car_ip, car_port)
    
    # 程序用时
    espect_time = time.time() - start_time
    print(f"✅ 测试完成，耗时{espect_time:.2f}秒")


if __name__ == "__main__":
    main()