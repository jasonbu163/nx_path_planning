# TCP 客户端

# 系统路径
import os
import sys
from pathlib import Path
# 调试输出路径信息
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))

from res_protocol_system import PacketBuilder, HeartbeatManager, NetworkManager, RESProtocol, PacketParser
import socket
import time

# HOST = 'localhost'  # The server's hostname or IP address
# PORT = 65432        # The port used

HOST = "192.168.8.30"  # The server's hostname or IP address
PORT = 2504        # The port used

# HOST = "192.168.123.187"  # The server's hostname or IP address
# PORT = 65432        # The port used

# HOST = "192.168.123.188"  # The server's hostname or IP address
# PORT = 2504        # The port used

builder = PacketBuilder(2)
parser = PacketParser()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as network:
    # 关键套接字优化
    network.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 禁用Nagle算法
    
    network.connect((HOST, PORT))  # 连接到服务器
    print(f"已连接到服务器 {HOST}:{PORT}")

    # message = "02 fd 01 6a 10 00 0b 4d 37 03 fc" # 调试软件正确样例
    # message = "02 fd 02 e8 10 00 0b 21 4f 03 fc"
    # message = "02 fd 01 6b 10 00 0b 4c cb 03 fc"
    # message = " 02 fd 01 6c 11 04 08 04 05 01 01 03 05 01 05 03 01 01 06 04 01 01 02 00 1d d5 a5 03 fc"
    
    bd_message = "02 fd 02 b3 12 00 13 bd 00 00 00 00 00 12 57 7e 03 fc"
    bd_message = bytes.fromhex(bd_message)
    
    # message_bytes = bytes.fromhex(message)
    message_bytes = b'\x02\xfd\x02\x65\x11\x26\x02\x04\x03\x01\x00\x04\x01\x01\x00\x00\x15\x60\x25\x03\xfc'

    print(f"发送数据: {message_bytes}")

    crc = builder._calculate_crc(message_bytes[:-4])
    print(f"CRC: {crc}")

    # 直接发送数据
    start_time = time.time()
    network.sendall(message_bytes)
    elapsed = time.time() - start_time
    print(f"发送完成，耗时: {elapsed:.6f}s")
    
    # 简化接收逻辑
    try:
        network.settimeout(5.0)  # 设置5秒超时
        response = network.recv(1024)
        parser.parse_task_response(response)
        print(f"接收到响应: {response}")
    except socket.timeout:
        print("响应超时，无数据返回")

    # 添加发送后立即关闭连接
    network.close()


# network = NetworkManager(HOST, PORT)
# heartbeat_manager = HeartbeatManager(network, builder)
# heartbeat_manager.start()