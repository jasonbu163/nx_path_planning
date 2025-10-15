# tests/test_db.py
from sys_path import setup_path
setup_path()

import asyncio
import time

from app.core.config import settings
from app.devices.fsm_devices_controller import CrossLayerTask
from app.devices.devices_controller import DevicesController
from app.res_system.connection import ConnectionAsync
from app.plc_system.controller import PLCController
from app.res_system.controller import ControllerBase as CarController

def test_1():
    plc = PLCController("192.168.101.1")
    car = CarController("192.168.101.12", 3389)
    devices_controller = CrossLayerTask(plc_controller=plc, car_controller=car)

    devices_controller.car_cross_layer(task_no=1, target_layer=2)

def test_2():
    plc_ip = settings.PLC_IP
    car_ip = settings.CAR_IP
    car_port = settings.CAR_PORT

    devices_controller = DevicesController(plc_ip, car_ip, car_port)

    # devices_controller.plc.connect()
    # devices_controller.plc.lift_move_by_layer_sync(task_no=140, layer=1)
    # devices_controller.plc.disconnect()

    # devices_controller.car.car_move(TASK_NO=128, TARGET_LOCATION="5,3,1")
    # devices_controller.car.car_move(TASK_NO=130, TARGET_LOCATION="6,3,1")
    # devices_controller.car.good_move(TASK_NO=130, TARGET_LOCATION="5,4,1")

    # devices_controller.car_cross_layer(task_no=1, target_layer=2)
    # devices_controller.task_inband(task_no=3, target_location="3,7,1")
    # devices_controller.task_outband(task_no=5, target_location="3,7,1")

async def test_3():
    # car = ConnectionBase(HOST="192.168.101.1", PORT=3389)
    car = ConnectionAsync(HOST="192.168.101.1", PORT=3389)

    await car.connect()
    await car.close()

def main():
    """同步测试"""

    start = time.time()

    # test_1()
    # test_2()

    elapsed = time.time() - start
    print(f"程序用时: {elapsed:.6f}s")
    

if __name__ == "__main__":
    main()

# async def main():
#     """异步测试"""
#     await test_3()

# if __name__ == "__main__":
#     asyncio.run(main())