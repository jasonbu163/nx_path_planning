# res_protocol_system/PacketParser.py
# -*- coding: utf-8 -*-
"""
RES+3.1 穿梭车通信协议上位机系统 - 模块化设计
按功能划分不同模块，便于团队协作维护
"""
import struct
import crcmod
from typing import Union

from .RESProtocol import RESProtocol, FrameType

# ------------------------
# 模块 3: 报文解析器
# 职责: 解析RES返回的各种报文
# 维护者: 协议开发工程师
# ------------------------

class PacketParser:
    def __init__(self):
        self.crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    
    ########################################
    # 通用工具
    ########################################

    def bytes_cut(
            self,
            INFO: Union[int, bytes]
            ) -> dict:
        """
        [字节解析器] 从一个字节（int或bytes类型）中提取位信息
    
        ::: param :::
            INFO: 输入的字节数据，可以是int类型（0-255）或长度为1的bytes类型
            
        ::: return :::
            dict: 包含提取的位信息的字典
                - high_4_bits: 高4位
                - low_4_bits: 低4位
                - low_4_high_2_bits: 低4位中的高2位
                - low_4_low_2_bits: 低4位中的低2位
                
        ::: raises :::
            Exception: 当INFO不是int或bytes类型时抛出异常
        """
        if isinstance(INFO, bytes):
            if len(INFO) != 1:
                raise Exception('[CAR] bytes类型参数长度必须为1')
            info = INFO[0]
        elif isinstance(INFO, int):
            if not (0 <= INFO <= 255):
                raise Exception('[CAR] int类型参数必须在0-255范围内')
            info = INFO
        else:
            raise Exception('[CAR] INFO必须是int或bytes类型')

        # 获取字节的整数值
        byte_value = info
        # print(f"原始字节: {byte_value:08b}")

        # 获取字节的前4位（高4位）
        high_4_bits = (byte_value >> 4) & 0x0F  # 右移4位并用0x0F掩码获取前4位
        # print(f"前4位: {high_4_bits:04b}")

        # 获取字节的后4位（低4位）
        low_4_bits = byte_value & 0x0F  # 使用掩码0x0F(1111)获取低4位
        # print(f"后4位: {low_4_bits:04b}")

        # 将后4位分成前2位和后2位
        low_4_high_2_bits = (low_4_bits >> 2) & 0x03  # 右移2位并获取前2位
        # print(f"后4位中的前2位: {low_4_high_2_bits:02b}")
        low_4_low_2_bits = low_4_bits & 0x03         # 使用掩码0x03(11)获取后2位
        # print(f"后4位中的后2位: {low_4_low_2_bits:02b}")

        return {
            "high_4_bits": high_4_bits,
            "low_4_bits": low_4_bits,
            "low_4_high_2_bits": low_4_high_2_bits,
            "low_4_low_2_bits": low_4_low_2_bits
        }
    
    def validate_packet(
            self,
            DATA: bytes
            ) -> bool:
        """
        [报文校验] - 验证报文完整性和CRC校验

        ::: param :::
            DATA: 报文数据

        ::: return :::
            bool: 是否通过校验
        """
        # 基本长度检查
        if len(DATA) < 10:
            return False
            
        # 检查头尾帧
        if DATA[:2] != RESProtocol.HEADER.value or DATA[-2:] != RESProtocol.FOOTER.value:
            return False
        
        # 提取报文中的CRC值（小端序）
        crc_received = DATA[-4] | (DATA[-3] << 8)  # 低位在前，高位在后

        # CRC校验
        crc_calculated = self.crc16(DATA[:-4])
        return crc_received == crc_calculated
    
    def parse_header(self, DATA: bytes) -> dict:
        """
        [解析包头] - 解析响应报文头部信息

        ::: param :::
            DATA: 报文数据

        ::: return :::
            dict: 解析后的报文数据
        """
        if len(DATA) < 5:  # 检查最小数据长度
            raise ValueError(f"数据长度不足，需至少5字节，实际收到{len(DATA)}字节")
            
        header_fields = struct.unpack_from('!2sBBB', DATA, 0)
        return {
            'first_frame': header_fields[0],
            'device_id': header_fields[1],
            'life': header_fields[2],
            'head_info': header_fields[3]
        }
    

    ########################################
    # 心跳包解析
    ########################################

    def parse_heartbeat_response(self, DATA: bytes) -> dict:
        """
        [解析心跳包] - 解析心跳响应报文(30)

        响应包格式:
            头(5) + 任务序号(1) + 执行结果(2) +
            当前坐标(3) + 行驶所在的段序号(1) + 当前条码值(4) + 
            小车状态(高位)/托板状态(低位)(1) + 换向状态(高位)/行驶方向(低位)(1) + 
            状态描述(1) + 有无托盘(1) +
            驱动器报警原因(4) + 
            长度(2) + CRC(2) + 尾帧(2)

        ::: param :::
            DATA: bytes 报文数据

        ::: return :::
            dict: 解析后的报文字典
        """
        # 打印报文
        if DATA:
            print(f"[CAR] 心跳响应报文: {DATA}")
        else:
            print("[CAR] 错误: 无数据")

        print(f"[CAR] 包长: {len(DATA)}")
        
        # 头(5)
        header = self.parse_header(DATA)

        # 剩余的数据
        payload = struct.unpack_from('!BHBBBBIBBBBIHH2s', DATA, 5)

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
            'msg_len': payload[12],
            'crc': payload[13],
            'end_frame': DATA[-2:]
        }
    
    def parse_hb_power_response(self, DATA: bytes) -> dict:
        """
        [解析心跳包] - 带电量信息(31)
        
        响应包格式:
            头(5) + 任务序号(1) + 执行结果(2) +
            当前坐标(3) + 行驶所在的段序号(1) + 当前条码值(4) + 
            小车状态(高位)/托板状态(低位)(1) + 换向状态(高位)/行驶方向(低位)(1) + 
            状态描述(1) + 有无托盘(1) +
            驱动器报警原因(4) + 电量(1) +
            长度(2) + CRC(2) + 尾帧(2)

        ::: param :::
            DATA: bytes  报文数据

        ::: return :::
            dict: 解析后的报文字典
        """
        # 打印报文
        if DATA:
            print(f"[CAR] 心跳响应报文: {DATA}")
        else:
            print("[CAR] 错误: 无数据")
        
        print(f"[CAR] 包长: {len(DATA)}")

        # 头(5)
        header = self.parse_header(DATA)

        # 剩余的数据
        payload = struct.unpack_from('!BHBBBBIBBBBIBHH2s', DATA, 5)

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
            'power': payload[12],
            'msg_len': payload[13],
            'crc': payload[14],
            'end_frame': DATA[-2:]
        }
    

    ########################################
    # 指令包解析
    ########################################

    def parse_command_response(self, DATA: bytes) -> dict:
        """
        [解析指令包] - 解析指令响应报文 - 定长18
        
        响应包格式:
            头(5) + 
            指令序号(1) + 执行结果(2) + 执行结果参数(4) + 
            长度(2) + CRC(2) + 尾帧(2)

        ::: param :::
            DATA: 任务包数据
        """
        if not self.validate_packet(DATA):
            return {
                'is_true': False,
                'msg': "非法报文"
                }
        print(f"[CAR] 包长: {len(DATA)}")

        # 头(5)
        header = self.parse_header(DATA)

        # 剩余的数据
        payload = struct.unpack_from('!BHIHH2s', DATA, 5)
        
        return {
            **header,
            'cmd_no': payload[0],
            'result': payload[1],
            'result_param': payload[2],
            'msg_len': payload[3],
            'crc': payload[4],
            'end_frame': payload[5]
        }
    

    ########################################
    # SCADA包解析
    ########################################

    def parse_scada_data(self, data) -> dict:
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
    
    ########################################
    # 任务包解析
    ########################################

    def parse_task_response(self, DATA: bytes) -> dict:
        """
        [解析任务包] - 解析任务响应报文 - 定长14

        响应包格式:
            头(5) + 
            任务号(1) + 执行结果(2) + 
            长度(2) + CRC(2) + 尾帧(2)

        ::: param :::
            DATA: 任务包数据
        """
        if not self.validate_packet(DATA):
            return {
                'is_true': False,
                'msg': "非法报文"
                }
        print(f"[CAR] 包长: {len(DATA)}")

        # 头(5)
        header = self.parse_header(DATA)

        # 剩余的数据
        payload = struct.unpack_from('!BHHH2s', DATA, 5)
        
        return {
            **header,
            'task_no': payload[0],
            'result': payload[1],
            'msg_len': payload[2],
            'crc': payload[3],
            'end_frame': payload[4]
        }
    
    ########################################
    # DEBUG包解析
    ########################################

    def parse_debug_response(self, data: bytes) -> Union[dict, None]:
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
    
    ########################################
    # 包识别 - 除心跳包
    ########################################

    def parse_generic_response(self, DATA: bytes) -> Union[dict, None]:
        """
        [通用解析方法] - 用于分类报文, 心跳报文除外
        """
        if not self.validate_packet(DATA):
            return {'error': 'Invalid packet'}
            
        header = self.parse_header(DATA)
        if not header:
            return {'error': 'Header parse failed'}
            
        frame_type = header['head_info']
        
        if frame_type == FrameType.COMMAND.value:
            return self.parse_command_response(DATA)
        elif frame_type == FrameType.TASK.value:
            return self.parse_task_response(DATA)
        elif frame_type == FrameType.DEBUG.value:
            return self.parse_debug_response(DATA)
        else:
            return {
                'header': header,
                'warning': 'Unsupported frame type'
            }
        
    ########################################
    # 心跳包识别
    ########################################

    def classify_heartbeat(self, DATA: bytes) -> Union[dict, None]:
        """
        [通用解析方法] - 用于分类心跳报文，主要区分是否带电量
        """
        if not self.validate_packet(DATA):
            return {'error': 'Invalid packet'}
            
        header = self.parse_header(DATA)
        if not header:
            return {'error': 'Header parse failed'}
            
        head_info = header['head_info']
        head_info_dict = self.bytes_cut(head_info)
        frame_type = head_info_dict['high_4_bits']
        
        if frame_type == FrameType.HEARTBEAT.value:
            return self.parse_heartbeat_response(DATA)
        elif frame_type == FrameType.HEARTBEAT_WITH_BATTERY.value:
            return self.parse_hb_power_response(DATA)
        else:
            return {
                'header': header,
                'warning': 'Unsupported frame type'
            }
    
    ########################################
    # 统一包识别
    ########################################

    async def parse(self, data) -> Union[dict, None]:
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