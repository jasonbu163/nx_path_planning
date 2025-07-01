# res_protocol_system/PacketParser.py
# -*- coding: utf-8 -*-
"""
RES+3.1 穿梭车通信协议上位机系统 - 模块化设计
按功能划分不同模块，便于团队协作维护
"""
import struct
import crcmod

from .RESProtocol import RESProtocol

# ------------------------
# 模块 3: 报文解析器
# 职责: 解析RES返回的各种报文
# 维护者: 协议开发工程师
# ------------------------

class PacketParser:
    def __init__(self):
        self.crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0xFFFF)
    
    def validate_packet(self, data):
        """验证报文完整性和CRC校验"""
        # 基本长度检查
        if len(data) < 10:
            return False
            
        # 检查头尾帧
        if data[:2] != RESProtocol.HEADER or data[-2:] != RESProtocol.FOOTER:
            return False
        
        # CRC校验
        crc_received = struct.unpack_from('<H', data, -4)[0]
        crc_calculated = self.crc16(data[:-4])
        return crc_received == crc_calculated
    
    def parse_header(self, data):
        """
        解析通用报文头部
        格式:
            头帧(2) + 设备ID(1) + 生命(1) + 报文类型(1)
        """
        
        # 读取头部字段
        header_fields = struct.unpack_from('!HBBBBH', data, 0)
        
        return {
            # 'first_frame': hex(header_fields[0]),
            'device_id': header_fields[1],
            'life': header_fields[2],
            'frame_type': header_fields[3],
        }
    
    def parse_heartbeat_response(self, data):
        """
        解析心跳响应报文
        格式:
            头(5) + 任务序号(1) + 执行结果(2) +
            当前坐标(3) + 行驶所在的段序号(1) + 当前条码值(4) + 
            小车状态(高位)/托板状态(低位)(1) + 换向状态(高位)/行驶方向(低位)(1) + 
            状态描述(1) + 有无托盘(1)
            驱动器报警原因(4) + 
            长度(2) + CRC(2) + 尾帧(2)          
        """
        # 打印报文
        if data:
            print(f"[接收] 心跳响应报文: {data}")
        else:
            print("[接收] 错误: 无数据")

        # 头(5)
        header = self.parse_header(data)

        # 剩余的数据
        payload = struct.unpack_from('!BHBBBBIBBBBIHHH', data, 5)

        # current_location
        x = payload[2]
        y = payload[3]
        z = payload[4]
        
        return {
            **header,
            'cmd_no': payload[0],
            'resluct': payload[1],
            'current_location': (x, y, z),
            'current_segment': payload[5],
            'cur_barcode': payload[6],
            'car_status': payload[7] >> 4,
            'pallet_status': payload[7] & 0x0F,
            'reserve_status': payload[8] >> 4,
            'drive_direction': payload[8] & 0x0F,
            'status_description': payload[9],
            'have_pallet': payload[10],
            'driver_warning': payload[11],
            'battery_elec': payload[12] if header['frame_type'] == 10 else None,
            'msg_len': payload[12] if header['frame_type'] == 0 else payload[13]
        }
    
    def parse_command_response(self, data):
        """
        解析指令响应报文
        格式:
            头(8) + 
            执行结果参数(4) + 
            长度(2) + CRC(2) + 尾帧(2)
        """
        
        # 打印报文
        if data:
            print(f"[接收] 指令响应报文: {data}")
        else:
            print("[接收] 错误: 无数据")

        header = self.parse_header(data)
        fields = struct.unpack_from('!IH', data, 8)
        
        return {
            **header,
            'result_param': fields[0],
            'msg_len': fields[1]
        }
    
    def parse_scada_data(self, data):
        """解析SCADA系统参数报文"""
        # SCADA数据格式较复杂，此处为简化示例
        header = self.parse_header(data)
        
        # 实际实现需要按文档格式解析所有190字节数据
        return {
            **header,
            # 'battery_temp': data[20:28],  # 电池温度
            # 'run_time': struct.unpack_from('!H', data, 8)[0],
            # 'driving_speed': struct.unpack_from('!h', data, 10)[0],
            # 'error_msg': data[100]
        }
    
def main():
    parser = PacketParser()

    # 测试解析报文头
    # header_data = parser.parse_header(b'\x02\xfd\x01\xc3\x00\x00\x00\x00')
    # print(f'解析报文头: {header_data}')

    # 测试解析心跳报文
    # b'\x02\xfd\x01\xc3\x00\x00\x00\x00'  # 包头(8)
    # b'\xff\xff\x1f'
    # b'\x00'
    # b'\x00\x01\xb2\x18'
    # b'\x30\x20\x00\x01'
    # b'\x00\x00\x00\x00'
    # b'\x00\x1e\x9e\xd8\x03\xfc' #包尾(6) 
    data_1 = b'\x02\xfd\x01\xc3\x00\x00\x00\x00' +\
        b'\xff\xff\x1f' +\
        b'\x00' +\
        b'\x00\x01\xb2\x18' +\
        b'\x30\x20\x00\x01' +\
        b'\x00\x00\x00\x00' +\
        b'\x00\x1e\x9e\xd8\x03\xfc'
    heartbeat_data = parser.parse_heartbeat_response(data_1)
    print(f'解析心跳报文: {heartbeat_data}')

    # 测试解析指令响应报文
    # data_2 = b'\x02\xfd\x01\x06\x02\x26\x00\x01\x00\x00\x00\x00\x00\x12\x9b\x52\x03\xfc'
    # command_data = parser.parse_command_response(data_2)
    # print(f'解析指令响应报文: {command_data}')

    # 测试解析SCADA数据报文
    # data_3 = b'\x02\xfd\x01\x06\x02\x26\x00\x01\x00\x00\x00\x00\x00\x12\x9b\x52\x03\xfc'
    # scada_data = parser.parse_scada_data(data_3)
    # print(f'解析SCADA数据报文: {scada_data}')

if __name__ == '__main__':
    main()