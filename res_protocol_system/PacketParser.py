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
        self.crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    
    def validate_packet(self, data):
        """验证报文完整性和CRC校验"""
        # 基本长度检查
        if len(data) < 10:
            return False
            
        # 检查头尾帧
        if data[:2] != RESProtocol.HEADER or data[-2:] != RESProtocol.FOOTER:
            return False
        
        # 提取报文中的CRC值（小端序）
        crc_received = data[-4] | (data[-3] << 8)  # 低位在前，高位在后

        # CRC校验
        crc_calculated = self.crc16(data[:-4])
        return crc_received == crc_calculated
    
    def parse_header(self, data):
        """解析协议头"""
        if len(data) < 5:  # 检查最小数据长度
            raise ValueError(f"数据长度不足，需至少5字节，实际收到{len(data)}字节")
            
        header_fields = struct.unpack_from('!2sBBB', data, 0)
        return {
            'header': header_fields[0],
            'device_id': header_fields[1],
            'life': header_fields[2],
            'type': header_fields[3]
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
            # 'battery_elec': payload[12] if header['frame_type'] == 10 else None,
            # 'msg_len': payload[12] if header['frame_type'] == 0 else payload[13]
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
    
    def parse_task_response(self, data):
        """解析任务响应报文"""
        if not self.validate_packet(data):
            return None
            
        header = self.parse_header(data)
        if not header:
            return None
            
        # 任务响应数据部分从第7字节开始
        payload_start = 7
        payload_end = len(data) - 4
        
        if payload_end - payload_start < 4:
            print("任务响应报文数据部分不足4字节")
            return None
            
        payload = data[payload_start:payload_end]
        
        # 解析任务响应字段
        task_no = payload[0] if len(payload) > 0 else 0
        result = payload[1] if len(payload) > 1 else 0
        current_segment = payload[2] if len(payload) > 2 else 0
        segment_count = payload[3] if len(payload) > 3 else 0
        
        return {
            **header,
            'task_no': task_no,
            'result': result,
            'current_segment': current_segment,
            'segment_count': segment_count
        }
    
    def parse_debug_response(self, data):
        """解析调试命令响应报文"""
        if not self.validate_packet(data):
            return None
            
        header = self.parse_header(data)
        if not header:
            return None
            
        # 调试响应数据部分从第7字节开始
        payload_start = 7
        payload_end = len(data) - 4
        
        if payload_end - payload_start < 8:
            print("调试响应报文数据部分不足8字节")
            return None
            
        payload = data[payload_start:payload_end]
        
        # 解析调试响应字段
        task_no = payload[0] if len(payload) > 0 else 0
        cmd_no = payload[1] if len(payload) > 1 else 0
        cmd_id = payload[2] if len(payload) > 2 else 0
        sub_cmd_id = payload[3] if len(payload) > 3 else 0
        param = struct.unpack('!I', payload[4:8])[0] if len(payload) >= 8 else 0
        
        return {
            **header,
            'task_no': task_no,
            'cmd_no': cmd_no,
            'cmd_id': cmd_id,
            'sub_cmd_id': sub_cmd_id,
            'param': param
        }
    
    def parse_generic_response(self, data):
        """通用解析方法"""
        if not self.validate_packet(data):
            return {'error': 'Invalid packet'}
            
        header = self.parse_header(data)
        if not header:
            return {'error': 'Header parse failed'}
            
        frame_type = header['frame_type']
        
        if frame_type == RESProtocol.FrameType.HEARTBEAT:
            return self.parse_heartbeat_response(data)
        elif frame_type == RESProtocol.FrameType.COMMAND:
            return self.parse_command_response(data)
        elif frame_type == RESProtocol.FrameType.TASK:
            return self.parse_task_response(data)
        elif frame_type == RESProtocol.FrameType.DEBUG:
            return self.parse_debug_response(data)
        else:
            return {
                'header': header,
                'warning': 'Unsupported frame type'
            }
    
    async def parse(self, data):
        """解析数据包"""
        try:
            # 如果是异步方法返回的数据，需要await
            if hasattr(data, '__await__'):
                data = await data
                
            # 检查数据长度
            if not isinstance(data, bytes):
                raise ValueError(f"数据类型错误，需为bytes类型，实际收到{type(data)}")
                
            if len(data) < 5:
                raise ValueError(f"数据长度不足，需至少5字节，实际收到{len(data)}字节")
                
            # 解析协议头
            header = self.parse_header(data)
            # 解析数据体
            body = self.parse_generic_response(data)
            
            return {
                'header': header,
                'body': body
            }
        except Exception as e:
            print(f"解析数据包时出错: {str(e)}")
            return None

# def main():
#     parser = PacketParser()

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
    # data_1 = b'\x02\xfd\x01\xc3\x00\x00\x00\x00' +\
    #     b'\xff\xff\x1f' +\
    #     b'\x00' +\
    #     b'\x00\x01\xb2\x18' +\
    #     b'\x30\x20\x00\x01' +\
    #     b'\x00\x00\x00\x00' +\
    #     b'\x00\x1e\x9e\xd8\x03\xfc'
    # heartbeat_data = parser.parse_heartbeat_response(data_1)
    # print(f'解析心跳报文: {heartbeat_data}')

    # 测试解析指令响应报文
    # data_2 = b'\x02\xfd\x01\x06\x02\x26\x00\x01\x00\x00\x00\x00\x00\x12\x9b\x52\x03\xfc'
    # command_data = parser.parse_command_response(data_2)
    # print(f'解析指令响应报文: {command_data}')

    # 测试解析SCADA数据报文
    # data_3 = b'\x02\xfd\x01\x06\x02\x26\x00\x01\x00\x00\x00\x00\x00\x12\x9b\x52\x03\xfc'
    # scada_data = parser.parse_scada_data(data_3)
    # print(f'解析SCADA数据报文: {scada_data}')

# if __name__ == '__main__':
#     main()