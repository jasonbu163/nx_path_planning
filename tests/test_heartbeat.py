# tests/test_heartbeat.py

import sys_path
sys_path.setup_path()

from res_protocol_system import PacketBuilder, PacketParser
from res_protocol_system.RESProtocol import RESProtocol, FrameType, WorkCommand, CarStatus
from devices.car_controller import CarController
from devices.service_asyncio import DevicesService


builder = PacketBuilder(2)

# packet = builder.heartbeat()
# packet = builder.build_heartbeat()

# 带电量心跳
# packet = builder.build_heartbeat(FrameType.HEARTBEAT_WITH_BATTERY)

# builder.location_change(2, 189, "1,1,1")

# import devices.service_asyncio as service
# sev = service.DevicesService("192.168.1.100", "192.168.1.100", 5000)
# a = sev.location_change("1,1,1")

# [CAR] 位置更改指令: b'\x02\xfd\x02\x01\x12\x02\xbdP\x00\x01\x01\x01\x00\x12\xc8b\x03\xfc'
# [CAR] 调试指令报文: b'\x02\xfd\x02\x01\x12\x02\xbdP\x00\x01\x01\x01\x00\x12\xc8b\x03\xfc'

# print(RESProtocol.VERSION.value)

# a = builder._pack_pre_info(FrameType.HEARTBEAT.value)
# print(a)

# map = [
#     [1,1,1,0],
#     [4,1,1,5],
#     [4,3,1,6],
#     [5,3,1,2],
#     ]
# map = [[1,1,1,0]]
# builder.build_task(1, map)

# builder.build_work_command(2, 189, WorkCommand.UPDATE_CAR_COORDINATES.value, [0,1,1,1])
# [CAR] 工作指令报文: b'\x02\xfd\x02\x01\x12\x02\xbdP\x00\x01\x01\x01\x00\x12\xc8b\x03\xfc'

# builder.location_change(2, 189, "1,1,1")
# [CAR] 位置更改指令: b'\x02\xfd\x02\x01\x12\x02\xbdP\x00\x01\x01\x01\x00\x12\xc8b\x03\xfc'

# [2025-07-28 18:13:45,865 -  INFO] 
# [CAR] 调试指令报文: b'\x02\xfd\x02\x01\x12\x02\xbdP\x00\x01\x01\x01\x00\x12\xc8b\x03\xfc'

# from devices.car_controller import CarController

# car = CarController("192.168.8.10", 50001)
# print(car._car_id)

# 响应心跳包
hb_msg =  b'\x02\xfd\x01\xc3\x00\x00\x00\x00\xff\xff\x1f\x00\x00\x01\xb2\x18\x30\x20\x00\x01\x00\x00\x00\x00\x00\x1e\x9e\xd8\x03\xfc'
# 带电量心跳包
power_msg =  b'\x02\xfd\x01\xc3\x00\x00\x00\x00\xff\xff\x1f\x00\x00\x01\xb2\x18\x30\x20\x00\x01\x00\x00\x00\x00\x12\x00\x1e\x9e\xd8\x03\xfc'
# 任务响应包
task_msg = b'\x02\xfd\x01\x6c\x01\x04\x00\x01\x00\x0e\xc0\x86\x03\xfc'
# 指令响应包
cmd_msg = b'\x02\xfd\x01\x06\x02\x26\x00\x01\x00\x00\x00\x00\x00\x12\x9b\x52\x03\xfc'

parser = PacketParser()
# msg = parser.parse_heartbeat_response(hb_msg)
msg = parser.parse_hb_power_response(power_msg)
# msg = parser.parse_task_response(task_msg)
# msg = parser.parse_command_response(cmd_msg)
msg = {
    'power': msg['power'],
    'msg': "ok"
       }
print(msg)