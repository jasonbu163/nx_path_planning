# tests/test_devices_controller.py

import sys_path
sys_path.setup_path()

import asyncio
import time

import config
from devices.devices_controller import DevicesController
from devices.plc_controller import PLCController
from devices.car_controller import CarController
from devices.plc_enum import PLCAddress

async def test_plc_controller(PLC_IP):
    """测试PLC控制器"""
    plc = PLCController(PLC_IP)
    await plc.async_connect()

    is_qrcode = plc.read_db(11, int(PLCAddress.SCAN_CODE_RD.value), 2)
    plc.logger.info(f"🙈 是否扫到码: {is_qrcode}")

    code = b''
    for code_db_addr in range(24, 29):
        items = plc.read_db(11, code_db_addr, 1)
        code += items
    plc.logger.info(f"🙈 扫码内容: {code}")
    if code == b'A0007':
        plc.logger.info("🚧 开始入库")
        plc.inband_to_lift()
        plc.logger.info("🚧 入库中...")
        time.sleep(1)
        await plc.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1020.value, 1)
        plc.logger.info("✅ 入库完成")
    else:
        plc.logger.error("❌ 托盘识别错误，请检查托盘是否扫到二维码。")
        await plc.async_disconnect()
        return False
    
    plc.logger.info("🚧 开始出库")
    plc.lift_to_outband()
    plc.logger.info("🚧 出库中...")
    await plc.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_MAN.value, 1)
    plc.logger.info("✅ 出库完成")

    await plc.async_disconnect()

async def test_car_controller(CAR_IP, CAR_PORT):
    """测试车辆控制器"""
    car = CarController(CAR_IP, CAR_PORT)
    await car.car_current_location(1)
async def test_devices_controller(PLC_IP, CAR_IP, CAR_PORT):
    
    # 创建设备控制器
    d_c = DevicesController(PLC_IP, CAR_IP, CAR_PORT)
    
    # 开启PlC连接
    await d_c.plc.async_connect()

    # 开始测试
    await d_c.car_cross_layer(TASK_NO=1, TARGET_LAYER=2)
    # await d_c.task_inband(TASK_NO=2, TARGET_LOCATION="1,1,2")
    # await d_c.task_outband(TASK_NO=3, TARGET_LOCATION="1,1,2")
    
    # 关闭PlC连接
    await d_c.plc.async_disconnect()
async def main():
    plc_ip = config.PLC_IP
    car_ip = config.CAR_IP
    car_port = config.CAR_PORT

    # 开始测试时间
    start_time = time.time()

    for i in range(24, 44):
        print(i)
    # await test_plc_controller(plc_ip)
    # await test_car_controller(car_ip, car_port)
    # await test_devices_controller(plc_ip, car_ip, car_port)
    espect_time = time.time() - start_time
    print(f"✅ 测试完成，耗时{espect_time:.2f}秒")


if __name__ == "__main__":
    asyncio.run(main())