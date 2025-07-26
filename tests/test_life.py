# tests/test_life.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import struct
import asyncio
from async_tcp_client_module import AsyncTCPClient
from res_protocol_system import PacketBuilder, RESProtocol, PacketParser
from devices.service_asyncio import DevicesService
from map_core import PathCustom


class IntCounter:
    def __init__(self):
        self.count = 0
        self.max_val = 255

    def __call__(self):
        self.count = (self.count % self.max_val) + 1
        time.sleep(1)
        return struct.pack("B", self.count)


# 生命周期
counter = IntCounter()

# 用来调crc和报文长度计算
builder = PacketBuilder(2)
# 解析报文
parser = PacketParser()


def _pack_pre_info(frame_type):
    """
    构建报文前段信息
    格式: 报文版本(4bit) 报文类型(4bit)
    """
    version_type = (RESProtocol.VERSION << 4) | (frame_type & 0x0F)
    return struct.pack("!B", version_type)


# 心跳报文
def heartbeat():
    header = b"\x02\xfd"
    device_id = struct.pack("B", 2)
    message = b"\x10\x00\x0b"
    footer = b"\x03\xfc"
    data = header + device_id + counter() + message
    crc = builder._calculate_crc(data)
    packet = data + crc + footer
    return packet


# print(heartbeat())
# print(message)
# for i in range(257):
#     # print(counter())  # 输出1-256，然后回到1
#     data = header + device_id + counter() + message
#     crc = builder._calculate_crc(data)
#     packet = data + crc + footer
#     print(packet)


# 更换位置指令报文
def location_change(location):
    """
    构建调试指令报文
    固定长度19字节
    :param cmd_id: (x, y, z)
    :return: 调试指令报文
    """

    # 构建基础头部
    header = RESProtocol.HEADER
    device_id = struct.pack("B", 2)
    life = counter()
    packet_info = _pack_pre_info(RESProtocol.FrameType.COMMAND)

    # 调试指令信息
    # task_no = 2
    # cmd_no = 189
    # cmd = 80
    # cmd_info = struct.pack('!BBB', task_no, cmd_no, cmd)
    cmd_info = b"\x02\xbd\x50"

    # 位置数据
    x, y, z = location[0], location[1], location[2]
    # 位置编码: X(8位) | Y(8位) | Z(8位) | 动作(8位)
    position = struct.pack("!BBBB", 0, x, y, z)
    print("位置编码: ", position)

    # 组合数据部份
    payload = cmd_info + position

    # 构建数据内容
    data_part = (
        header
        + device_id
        + life
        + packet_info
        + payload
        + builder._data_length(device_id + life + packet_info + payload)
    )

    # 计算CRC
    crc = builder._calculate_crc(data_part)

    # 基础尾部字段
    footer = RESProtocol.FOOTER

    # 组合完整报文
    packet = data_part + crc + footer
    print("[发送] 调试指令报文: ", packet)

    # 返回报文
    return packet

def segments_task_len(segments):
    """
    计算任务段数
    :param segments: 路径段列表 [(x, y, z, action), ...]
    :return: 任务段数
    """
    task_len = len(segments)
    print(f"任务段数(无动作): {task_len}")
    for segment in segments:
        if segment[3] != 0:
            task_len += 1
    print(f"任务段数(含动作): {task_len}")
    return task_len

def add_pick_drop_actions(point_list):
    """
    在路径列表的起点和终点添加货物操作动作
    :param point_list: generate_point_list()生成的路径列表
    :return: 修改后的路径列表（起点动作=1提起，终点动作=2放下）
    """
    # 确保路径至少有两个点
    if len(point_list) < 2:
        return point_list
    
    # 创建列表副本防止修改原数据
    new_list = [tuple(point) for point in point_list]
    
    # 修改起点动作（索引0）为1（提起货物）
    new_list[0] = tuple(new_list[0][:3]) + (1,)
    
    # 修改终点动作（索引-1）为2（放下货物）
    new_list[-1] = tuple(new_list[-1][:3]) + (2,)
    
    return new_list


# 任务报文
def build_task(task_no, segments):
    """
    构建整体任务报文
    :param task_no: 任务序号 (1-255)
    :param segments: 路径段列表 [(x, y, z, action), ...]
    :return: 任务报文
    """
    # 构建基础头部
    header = b"\x02\xfd"
    device_id = struct.pack("B", 2)
    life = counter()
    packet_info = _pack_pre_info(RESProtocol.FrameType.TASK)

    # 构建数据内容
    # 计算动态长度: 4字节*段数
    segment_count = segments_task_len(segments)
    # print("任务段数: ", segment_count)
    # 添加任务数据
    payload = struct.pack("!BB", task_no, segment_count)
    # 添加路径段
    for segment in segments:
        x, y, z, action = segment
        # 位置编码: X(8位) | Y(8位) | Z(8位) | 动作(8位)
        # position = (x << 24) | (y << 16) | (z << 8) | action
        # print("位置编码: ", hex(position))
        # payload += struct.pack('!I', position)
        position = struct.pack("!BBBB", x, y, z, action)
        print("位置编码: ", position)
        payload += position

    # 计算数据段长度
    data_length = builder._data_length(device_id + life + packet_info + payload)

    # 组合数据段
    data_part = header + device_id + life + packet_info + payload + data_length

    # 计算CRC
    crc = builder._calculate_crc(data_part)

    # 基础尾部字段
    footer = RESProtocol.FOOTER

    # 组装报文
    packet = data_part + crc + footer
    print("[发送] 整体任务报文: ", packet)

    # 返回报文
    return packet


# 确认执行任务报文
def do_task(task_no, segments):
    """
    构建整体任务报文
    :param task_no: 任务序号 (1-255)
    :param segments: 路径段列表 [(x, y, z, action), ...]
    :return: 任务报文
    """
    # 构建基础头部
    header = RESProtocol.HEADER
    device_id = struct.pack("B", 2)
    life = counter()
    packet_info = _pack_pre_info(RESProtocol.FrameType.COMMAND)

    # 构建数据内容
    # 任务号
    task_no = struct.pack("B", task_no)
    cmd_no = 44
    cmd = 144
    cmd_info = struct.pack("!BB", cmd_no, cmd)
    # 计算动态长度: 4字节*段数
    segment_count = struct.pack(">I", segments_task_len(segments))
    # print("任务段数: ", segment_count)

    payload = task_no + cmd_info + segment_count

    # 计算数据段长度
    data_length = builder._data_length(device_id + life + packet_info + payload)

    # 组合数据段
    data_part = header + device_id + life + packet_info + payload + data_length

    # 计算CRC
    crc = builder._calculate_crc(data_part)

    # 基础尾部字段
    footer = RESProtocol.FOOTER

    # 组装报文
    packet = data_part + crc + footer
    print("[发送] 整体任务报文: ", packet)

    # 返回报文
    return packet


async def my_app_1():
    # HOST = "192.168.8.30"
    # PORT = 2504
    # client = AsyncTCPClient(HOST, PORT)
    PLC_IP = "192.168.8.10"
    CAR_IP = "192.168.8.30"
    CAR_PORT = 2504
    client = DevicesService(PLC_IP, CAR_IP, CAR_PORT)
    map = PathCustom()

    # 心跳报文
    # for i in range(2):
    #     packet = heartbeat()
    #     if await client.connect():
    #         await client.send_message(packet)
    #         response = await client.receive_message()
    #         if response:
    #             msg = parser.parse_heartbeat_response(response)
    #             print(msg)
    #             await client.close()

    # 初始化小车位置
    # car_location = (6, 3, 2)
    # packet = location_change(car_location)
    # print(packet)
    # if await client.connect():
    #     await client.send_message(packet)
    #     response = await client.receive_message()
    #     print(response)
    #     if response:
    #         # msg = parser.parse_heartbeat_response(response)
    #         # msg = parser.parse_task_response(response)
    #         # msg = parser.parse_task_response(response)
    #         # print(msg)
    #         await client.close()

    # 任务报文
    import random

    task_no = random.randint(1, 100)
    # segments = [(1, 1, 1, 0), (4, 1, 1, 5), (4, 3, 1, 6), (6, 3, 1, 0)]
    # segments = [(5, 3, 1, 0), (4, 3, 1, 5)]
    start = "5,1,1"
    target = "5,3,1"
    segments = map.build_segments(start, target)
    print(segments)

    # 用 DeviceService()
    task_packet = client.build_task(task_no, segments)
    if await client.car_connect():
        await client.car_send_message(task_packet)
        response = await client.car_receive_message()
        if response:
            # msg = parser.parse_task_response(response)
            # print(msg)
            do_packet = client.do_task(task_no, segments)
            await client.car_send_message(do_packet)
            response = await client.car_receive_message()
            if response:
                # msg = parser.parse_task_response(response)
                # print(msg)
                await client.car_close()

    # 用 AsyncTCPClient()
    # task_packet = build_task(task_no, segments)
    # if await client.connect():
    #     await client.send_message(task_packet)
    #     response = await client.receive_message()
    #     if response:
    #         # msg = parser.parse_task_response(response)
    #         # print(msg)
    #         # time.sleep(0.5)
    #         do_packet = do_task(task_no, segments)
    #         await client.send_message(do_packet)
    #         response = await client.receive_message()
    #         if response:
    #             # msg = parser.parse_task_response(response)
    #             # print(msg)
    #             await client.close()


async def my_app_2():
    PLC_IP = "192.168.8.10"
    CAR_IP = "192.168.8.30"
    CAR_PORT = 2504
    client = DevicesService(PLC_IP, CAR_IP, CAR_PORT)

    # 心跳报文
    msg = await client.send_heartbeat(2)
    print(msg)

    # 初始化小车位置
    # car_location = (5, 3, 1)
    # await client.car_change_location(car_location)

    # 任务报文
    car_target = "4,1,1"
    # await client.car_move(car_target)
    await client.good_move(car_target)

# asyncio.run(my_app_1())

# asyncio.run(my_app_2())