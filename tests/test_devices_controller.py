# tests/test_devices_controller.py

import sys_path
sys_path.setup_path()

import asyncio

from devices.devices_controller import DevicesController

async def test_devices_controller():
    d_c = DevicesController(PLC_IP="192.168.1.1", CAR_IP="192.168.1.1", CAR_PORT=502)
    
    # 开启PlC连接
    await d_c.async_connect()

    # 开始测试
    await d_c.car_cross_layer(TASK_NO=1, TARGET_LAYER=2)
    await d_c.task_inband(TASK_NO=2, TARGET_LOCATION="1,1,2")
    await d_c.task_outband(TASK_NO=3, TARGET_LOCATION="1,1,2")

    # 关闭PlC连接
    await d_c.async_disconnect()