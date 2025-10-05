# tests/test_db.py
from sys_path import setup_path
setup_path()

import asyncio

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
    devices_controller = DevicesController(plc_ip="192.168.244.1", car_ip="192.168.101.12", car_port=3389)

    devices_controller.car_cross_layer(task_no=1, target_layer=2)

async def test_3():
    # car = ConnectionBase(HOST="192.168.101.1", PORT=3389)
    car = ConnectionAsync(HOST="192.168.101.1", PORT=3389)

    await car.connect()
    await car.close()

def main():
    """同步测试"""
    test_1()
    # test_2()

if __name__ == "__main__":
    main()

# async def main():
#     """异步测试"""
#     await test_3()

# if __name__ == "__main__":
#     asyncio.run(main())