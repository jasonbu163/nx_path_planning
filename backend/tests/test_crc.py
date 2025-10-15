# 系统路径
import os
import sys
from pathlib import Path
# 调试输出路径信息
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))

import crcmod
import struct
from res_protocol_system import PacketBuilder

build = PacketBuilder(2)

# 定义 CRC16-Modbus 参数
crc16_modbus = crcmod.mkCrcFun(
    poly=0x18005,       # CRC-16-Modbus 多项式 (0x8005 位反转后为 0xA001)
    rev=True,           # 输入数据反转（低位在前）
    initCrc=0xFFFF,     # 初始值
    xorOut=0x0000       # 结果异或值
)

def car_crc(message):
    """CRC16计算
    :message: 待计算数据 
    :return: CRC16值
    """
    message_bytes = bytes.fromhex(message)
    print(f"message_bytes: {message_bytes} ")

    # 需校验的数据范围（前7字节）
    # data = bytes.fromhex("02 FD 02 C3 10 00 0B")
    # 取数据除去后4个字节
    data = message_bytes[:-4]
    print("需校验的数据范围：", data)
    crc_calculated = crc16_modbus(data)  # 计算 CRC
    # 示例报文中的 CRC 值（0x6CAB，低位在前高位在后）
    # crc_expected = 0xAB6C  # 实际值：低位 0x6C + 高位 0xAB = 0xAB6C

    # 取倒数第三和第四个字节
    # 高8位
    crc_expected_high = message_bytes[-4]
    # print(f"实际 CRC 值高8位：{crc_expected_high:X}")
    # 低8位
    crc_expected_low = message_bytes[-3]
    # print(f"实际 CRC 值低8位：{crc_expected_low:X}")
    # print(f"实际 CRC 值：0x{crc_expected_high:X}{crc_expected_low:X}")
    crc_expected = (crc_expected_low << 8) | crc_expected_high
    # print(f"实际 CRC 值：0x{crc_expected:X}")

    # 输出结果
    print(f"计算 CRC: 0x{crc_calculated:X}")  # 应为 0xAB6C
    print(f"匹配结果: {'成功' if crc_calculated == crc_expected else '失败'}")
    crc_calculated_high, crc_calculated_low = struct.unpack('<HH', crc_calculated)
    # crc_calculated_high = 
    # crc_calculated = (crc_calculated_low << 8) | crc_calculated_high

    return crc_calculated


# 调试软件正确样例
message = "02 fd 01 6a 10 00 0b 4d 37 03 fc"
# message = "02 fd 01 6b 10 00 0b 4c cb 03 fc"
# message = " 02 fd 01 6c 11 04 08 04 05 01 01 03 05 01 05 03 01 01 06 04 01 01 02 00 1d d5 a5 03 fc"
print(f"输入报文: {message}")
message = bytes.fromhex(message)
print(f"输入报文: {message}")
cut_message = message[:-4]
print(f"要计算的报文字段内容: {cut_message}")
message_crc = build._calculate_crc(cut_message)
print(f"返回crc: {message_crc}")



# message_crc = car_crc(message)
# print(f"返回crc: 0x{message_crc}")