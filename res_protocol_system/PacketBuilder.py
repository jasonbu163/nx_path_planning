# res_protocol_system/PacketBuilder.py
import struct
import crcmod
from .RESProtocol import RESProtocol
import logging

# ------------------------
# 模块 2: 报文构建器
# 职责: 创建各种类型的协议报文
# 维护者: 协议开发工程师
# ------------------------

class PacketBuilder:
    def __init__(self, device_id=1):
        self.device_id = device_id
        self.life_counter = 0
        self.crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)

        # 配置日志
        logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s'
                )
        self.logger = logging.getLogger(__name__)

    ########################################
    # 包头构建工作
    ########################################
    def _increment_life(self):
        """更新生命计数器"""
        self.life_counter = (self.life_counter + 1) % 256
        return self.life_counter
    
    def _pack_pre_info(self, frame_type):
        """
        构建报文前段信息
        格式: 设备ID(1) + 生命(1) + 版本类型(1)
        """
        version_type = (RESProtocol.VERSION << 4) | (frame_type & 0x0F)
        # return struct.pack('!BBB',
        #                   self.device_id,
        #                   self._increment_life(),
        #                   version_type)
        return struct.pack('!BBB',
                          self.device_id,
                          1,
                          version_type)
    
    def _pack_type_info(self, frame_type):
        """
        构建版本信息
        如果使用_pack_pre_info则不需要
        格式: 报文版本(4bit) 报文类型(4bit)
        """
        version_type = (RESProtocol.VERSION << 4) | (frame_type & 0x0F)
        return struct.pack('!B',version_type)
    
    def _data_length(self, data: bytes):
        """
        计算报文长度
        """
        header_length = 2
        data_length = len(data)
        len_length = 2
        crc_length = 2
        footer_length = 2
        packet_length = header_length + data_length + len_length + crc_length + footer_length
        print('报文长度:', packet_length)
        return struct.pack('!H', packet_length)
    
    def _calculate_crc(self, data: bytes):
        """
        计算CRC校验位
        格式: 校验位(2)
        """
        crc = self.crc16(data)
        print('CRC16校验值:', hex(crc))
        return struct.pack('<H', crc)
    
    ########################################
    # 报文构建方法
    ########################################

    def segments_task_len(self, segments):
        """
        计算任务段数
        :param segments: 路径段列表 [(x, y, z, action), ...]
        :return: 任务段数
        """
        task_len = len(segments)
        self.logger.info(f"任务段数(无动作): {task_len}")
        for segment in segments:
            if segment[3] != 0:
                task_len += 1
        self.logger.info(f"任务段数(含动作): {task_len}")
        return task_len

    ################ 心跳报文 ################
    def heartbeat(self):
        header = RESProtocol.HEADER
        device_id = struct.pack('B', self.device_id)
        # life = struct.pack('B', self._increment_life())
        life = struct.pack('B', 1)
        message = b'\x10\x00\x0b'
        footer = RESProtocol.FOOTER
        data = header + device_id + life + message
        crc = self._calculate_crc(data)
        packet = data + crc + footer
        return packet
    
    def build_heartbeat(self, frame_type=RESProtocol.FrameType.HEARTBEAT):
        """
        构建心跳报文
        固定长度11字节
        """
        # 构建基础头部
        header = RESProtocol.HEADER
        pre_info = self._pack_pre_info(frame_type)
        
        # 计算数据段长度
        data_length = self._data_length(pre_info)
        
        # 组合数据段
        data_part = header+ pre_info + data_length

        # 计算CRC
        crc = self._calculate_crc(data_part)
        
        # 基础尾部字段
        footer = RESProtocol.FOOTER

        # 组装报文
        packet = header + data_part + crc + footer
        self.logger.info("[发送] 心跳报文: ", packet)

        # 返回报文
        return packet
    
    def build_task_command(self, task_no, segments):
        """
        构建整体任务报文
        :param task_no: 任务序号 (1-255)
        :param segments: 路径段列表 [(x, y, z, action), ...]
        :return: 任务报文
        """
        # 构建基础头部
        header = RESProtocol.HEADER
        pre_info = self._pack_pre_info(RESProtocol.FrameType.TASK)
        
        # 构建数据内容
        # 计算动态长度: 4字节*段数
        segment_count = len(segments)
        # print("任务段数: ", segment_count)
        # 添加任务数据
        payload = struct.pack('!BB', task_no, segment_count)
        # 添加路径段
        for segment in segments:
            x, y, z, action = segment
            # 位置编码: X(8位) | Y(8位) | Z(8位) | 动作(8位)
            # position = (x << 24) | (y << 16) | (z << 8) | action
            # print("位置编码: ", hex(position))
            # payload += struct.pack('!I', position)
            position = struct.pack('!BBBB', x, y, z, action)
            print("位置编码: ", position)
            payload += position
        
        # 计算数据段长度
        data_length = self._data_length(pre_info + payload)
        
        # 组合数据段
        data_part = pre_info + payload + data_length

        # 计算CRC
        crc = self._calculate_crc(data_part)
        
        # 基础尾部字段
        footer = RESProtocol.FOOTER

        # 组装报文
        packet = header + data_part + crc + footer
        print("[发送] 整体任务报文: ", packet)

        # 返回报文
        return packet

    def build_debug_command(self, cmd_id, sub_cmd_id=0, param=0):
        """
        构建调试指令报文
        固定长度19字节
        :param cmd_id: 主指令ID (0x9D, 0x9E等)
        :param sub_cmd_id: 次指令ID
        :param param: 参数值 (32位)
        :return: 调试指令报文
        """
        
        # 构建基础头部
        header = RESProtocol.HEADER
        pre_info = self._pack_pre_info(RESProtocol.FrameType.DEBUG)
        
        # 添加调试指令数据
        payload = struct.pack('!BBBBI', 
                                       0,  # 任务号(占位)
                                       self._increment_life(),  # 指令序号
                                       cmd_id, 
                                       sub_cmd_id, 
                                       param)
        
        # 构建数据内容
        data_part = pre_info + payload + self._data_length(pre_info + payload)
        
        # 计算CRC
        crc = self._calculate_crc(data_part)

        # 基础尾部字段
        footer = RESProtocol.FOOTER
        
        # 组合完整报文
        packet = header + data_part + crc + footer
        print("[发送] 调试指令报文: ", packet)
        
        # 返回报文
        return packet


def main():
    # 初始化
    pb = PacketBuilder(2)

    # 构建心跳报文
    heartbeat = pb.heartbeat()
    build_heartbeat = pb.build_heartbeat()
    print(f"[1] 心跳报文: {heartbeat}")
    print("#####################################")
    print(f"[2] 心跳报文: {build_heartbeat}")

    # 构建任务报文
    # task_no = 1
    # warehouse_segments = [
    #         (1, 2, 1, 0),    # 从(10,20)到下一个点的直行
    #         (1, 5, 1, 0),    # 直行到(10,50)
    #         (3, 5, 1, 1),    # 左转到(30,50)
    #         (3, 6, 1, 3),    # 提升货物
    #         (3, 8, 1, 0),    # 直行到(30,80)楼层1
    #         (3, 8, 1, 4),    # 下降货物
    #         (3, 8, 1, 5)     # 停止
    #     ]
    # task_cmd = pb.bulid_task_command(task_no=task_no, segments=warehouse_segments)
    # print(f'任务报文: {task_cmd}')

    # 构建调试命令报文
    # debug_cmd = pb.build_debug_command(cmd_id=0x01, sub_cmd_id=0x01, param=0x01)
    # print(f'调试命令报文: {debug_cmd}')

if __name__ == '__main__':
    main()