# res_protocol_system/PacketBuilder.py
import struct
import crcmod

from .res_protocol import (
    RESProtocol,
    FrameType,
    WorkCommand,
    ImmediateCommand
    )

# ------------------------
# 模块 2: 报文构建器
# 职责: 创建各种类型的协议报文
# 维护者: 协议开发工程师
# ------------------------

class PacketBuilder:
    """
    [报文构建器类] - 构建创建各种类型的协议报文
    """
    def __init__(self, device_id: int=1):
        """
        [初始化报文构建器]

        ::: param :::
            device_id: 设备ID
        """
        self.device_id = device_id
        self._life_counter = 0
        self.crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)


    ########################################
    # 包头构建工作
    ########################################
    
    def _increment_life(self) -> int:
        """
        [生命周期计数器] - 生命周期为1-256，超过256后重新开始计数

        ::: return :::
            self._life_counter
        """
        self._life_counter = (self._life_counter % 255) + 1
        return self._life_counter
    
    def _pack_pre_info(self, FRAME_TYPE) -> bytes:
        """
        [构建报文前段信息]
            格式: 设备ID(1字节) + 生命(1字节) + 版本&类型(1字节)
            版本&类型中包含，报文版本(4bit)和报文类型(4bit)

        ::: param :::
            FRAME_TYPE: 报文类型枚举, 如 RESProtocol.FRAME_TYPE.HEARTBEAT
        
        ::: return :::
            报文前段信息字节流
        """
        version_type = (RESProtocol.VERSION.value << 4) | (FRAME_TYPE & 0x0F)
        return struct.pack('!BBB',
                          self.device_id,
                          self._increment_life(),
                          version_type)
    
    def _pack_type_info(self, FRAME_TYPE: int) -> bytes:
        """
        [构建版本信息] - 如果使用_pack_pre_info则不需要

            格式: 报文版本(4bit) 报文类型(4bit)

        ::: param :::
            FRAME_TYPE: 报文类型枚举, 如 RESProtocol.FRAME_TYPE.HEARTBEAT

        ::: return :::
            返回报文版本和报文类型组合字节流
        """
        version_type = (RESProtocol.VERSION.value << 4) | (FRAME_TYPE & 0x0F)
        return struct.pack('!B',version_type)
    
    def _data_length(self, DATA: bytes) -> bytes:
        """
        [计算报文长度]
            报文 = header + [这里是输入的DATA] + [这里是计算后的值，报文的长度] + crc + footer


        ::: param :::
            DATA: 报文核心字段数据

        ::: return :::
            paclet_length: 报文长度字段（paclet_length转化成字节后，占两个字节再返回输出）
        """
        header_length = 2
        data_length = len(DATA)
        len_length = 2
        crc_length = 2
        footer_length = 2
        packet_length = header_length + data_length + len_length + crc_length + footer_length
        print(f"[CAR] 报文长度:{packet_length}")
        return struct.pack('!H', packet_length)
    
    def _calculate_crc(self, DATA: bytes) -> bytes:
        """
        [计算CRC校验位]

        格式: 校验位(2)
        """
        crc = self.crc16(DATA)
        print(f"[CAR] CRC16校验值: {hex(crc)}")
        return struct.pack('<H', crc)
    

    def _segments_task_len(self, SEGMENTS: list) -> int:
        """
        [计算任务段数]

        ::: param :::
            SEGMENTS: 路径段列表 [(x, y, z, action), ...]

        ::: return :::
            task_len: int, 任务段数
        """
        task_len = len(SEGMENTS)
        print(f"[CAR] 任务段数(无动作): {task_len}")
        for segment in SEGMENTS:
            if segment[3] != 0:
                task_len += 1
        print(f"[CAR] 任务段数(含动作): {task_len}")
        return task_len


    ########################################
    # 心跳报文
    ########################################

    def heartbeat(self) -> bytes:
        """
        [心跳报文] - 固定长度11字节
            默认的心跳报文，不带传参。
            如果想要获得电量显示，使用build_heartbeat()方法，并且传入对应的参数。

        ::: return :::
            packet: bytes 心跳报文
        """
        # 构建基础头部
        # 基础头字段
        header = RESProtocol.HEADER.value
        
        # 设备ID
        device_id = struct.pack('B', self.device_id)
        
        # 生命周期
        life = struct.pack('B', self._increment_life())
        
        # 报文版本 & 报文类型
        pack_type_info = self._pack_type_info(FrameType.HEARTBEAT.value)
        
        # 计算报文长度
        data = device_id + life + pack_type_info
        data_length = self._data_length(data)
        
        # 这个部份的组成是： packet_type_info(8) + data_length(16)
        # message = b'\x10\x00\x0b'
        
        # 组合数据段
        data_part = header + data + data_length
        # data_part = header + device_id + life + message
        
        # 计算CRC
        crc = self._calculate_crc(data_part)
        
        # 基础尾部字段
        footer = RESProtocol.FOOTER.value
        
        # 组装报文
        packet = data_part + crc + footer
        print(f"[CAR] 心跳报文: {packet}")
        
        # 返回报文
        return packet
    
    def build_heartbeat(
            self,
            FRAME_TYPE=FrameType.HEARTBEAT
            ) -> bytes:
        """
        [构建心跳报文] - 固定长度11字节，可传参，传入电量心跳报文类型
        
        !!! 注意 !!! 
            这里比较特殊, 传参为FrameType.HEARTBEAT, 
            不是FrameType.HEARTBEAT.value

        ::: param :::
            FRAME_TYPE: 报文类型

        ::: return :::
            packet: bytes, 心跳报文
        """
        # 构建基础头部
        header = RESProtocol.HEADER.value
        pre_info = self._pack_pre_info(FRAME_TYPE.value)
        
        # 计算数据段长度
        data_length = self._data_length(pre_info)
        
        # 组合数据段
        data_part = header + pre_info + data_length

        # 计算CRC
        crc = self._calculate_crc(data_part)
        
        # 基础尾部字段
        footer = RESProtocol.FOOTER.value

        # 组装报文
        packet = data_part + crc + footer
        print(f"[CAR] {FRAME_TYPE.name} 报文: {packet}")

        # 返回报文
        return packet
    
    ########################################
    # 任务报文
    ########################################
    
    def build_task(
            self,
            TASK_NO: int,
            SEGMENTS: list
            ) -> bytes:
        """
        [构建整体任务报文]

        ::: param :::
            TASK_NO: 任务序号 (1-255)
            SEGMENTS: 路径段列表 [(x, y, z, action), ...]

        ::: return :::
            packet: bytes, 任务报文
        """
        # 构建基础头部
        header = RESProtocol.HEADER.value
        pre_info = self._pack_pre_info(FrameType.TASK.value)
        
        # 构建数据内容
        print("[CAR] 任务序号: ", TASK_NO)

        # 计算动态长度: 4字节*段数
        segment_count = self._segments_task_len(SEGMENTS)
        print("[CAR] 任务段数: ", segment_count)
        
        # 添加任务数据
        payload = struct.pack('!BB', TASK_NO, segment_count)
        
        # 添加路径段
        for segment in SEGMENTS:
            x, y, z, action = segment
            # 位置编码: X(8位) | Y(8位) | Z(8位) | 动作(8位)
            # position = (x << 24) | (y << 16) | (z << 8) | action
            # print("位置编码: ", hex(position))
            # payload += struct.pack('!I', position)
            position = struct.pack('!BBBB', x, y, z, action)
            print(f"[CAR] 位置编码: {position}")
            payload += position
        
        # 计算数据段长度
        data_length = self._data_length(pre_info + payload)
        
        # 组合数据段
        data_part = header + pre_info + payload + data_length

        # 计算CRC
        crc = self._calculate_crc(data_part)
        
        # 基础尾部字段
        footer = RESProtocol.FOOTER.value

        # 组装报文
        packet = data_part + crc + footer
        print(f"[CAR] 整体任务报文: {packet}")

        # 返回报文
        return packet

    ########################################
    # 调试 - 指令报文
    ########################################

    def build_debug_command(
            self,
            TASK_NO: int,
            CMD_NO: int,
            CMD: bytes,
            SUB_CMD_ID: int=0,
            CMD_PARAM: list=[0,0,0,0],
            ) -> bytes:
        """
        [构建调试指令报文] - 固定长度19字节

        ::: param :::
            TASK_NO: 任务编号 (1-255)
            CMD_NO: 操作指令序号 (1-255)
            CMD: 主指令ID (0x9D, 0x9E等)
            SUB_CMD_ID: 次指令ID
            CMD_PARAM: 参数值 (32位)，输入一个列表四位整数的列表

        ::: return :::
            packet: bytes, 调试指令报文
        """
        
        # 构建基础头部
        header = RESProtocol.HEADER.value
        pre_info = self._pack_pre_info(FrameType.DEBUG.value)

        # 任务序号
        task_no = struct.pack('!B', TASK_NO)
        # 指令编号
        cmd_no = struct.pack('!B', CMD_NO)
        
        # 次指令ID
        sub_cmd_id = struct.pack('!B', SUB_CMD_ID)
        
        # 添加调试指令数据
        cmd_param = struct.pack(
            '!BBBB',
            CMD_PARAM[0],
            CMD_PARAM[1],
            CMD_PARAM[2],
            CMD_PARAM[3]
            )
        payload = task_no + cmd_no + CMD + sub_cmd_id + cmd_param
        
        # 计算数据段长度
        data_lenght = self._data_length(pre_info + payload)
        
        # 构建数据内容
        data_part = header + pre_info + payload + data_lenght
        
        # 计算CRC
        crc = self._calculate_crc(data_part)

        # 基础尾部字段
        footer = RESProtocol.FOOTER.value
        
        # 组装报文
        packet = data_part + crc + footer
        print(f"[CAR] 调试指令报文: {packet}")
        
        # 返回报文
        return packet
    

    ########################################
    # 工作 - 指令报文
    ########################################

    def build_work_command(
            self,
            TASK_NO: int,
            CMD_NO: int,
            CMD: bytes,
            CMD_PARAM: list=[0,0,0,0],
            ) -> bytes:
        """
        [构建工作指令报文] - 固定长度18字节

        ::: param :::
            TASK_NO: 任务编号 (1-255)
            CMD_NO: 操作指令序号 (1-255)
            CMD: 主指令ID (0x9D, 0x9E等)
            CMD_PARAM: 参数值 (32位)，输入一个列表四位整数的列表

        ::: return :::
            packet: bytes, 工作指令报文
        """
        
        # 构建基础头部
        header = RESProtocol.HEADER.value
        pre_info = self._pack_pre_info(FrameType.COMMAND.value)

        # 任务号
        task_no = struct.pack('!B', TASK_NO)
        print("[CAR] 任务号: ", task_no)
        
        # 指令编号
        cmd_no = struct.pack('!B', CMD_NO)
        
        #### 指令参数（32） ####
        # 添加调试指令数据
        cmd_param = struct.pack(
            '!BBBB',
            CMD_PARAM[0],
            CMD_PARAM[1],
            CMD_PARAM[2],
            CMD_PARAM[3]
            )
        payload = task_no + cmd_no + CMD + cmd_param
        
        # 计算数据段长度
        data_lenght = self._data_length(pre_info + payload)
        
        # 构建数据内容
        data_part = header + pre_info + payload + data_lenght
        
        # 计算CRC
        crc = self._calculate_crc(data_part)

        # 基础尾部字段
        footer = RESProtocol.FOOTER.value
        
        # 组装报文
        packet = data_part + crc + footer
        print(f"[CAR] 工作指令报文: {packet}")
        
        # 返回报文
        return packet
    
    def location_change(
            self,
            TASK_NO: int=2,
            LOCATION: str="255,255,31"
            ) -> bytes:
        """
        [更换位置] - 固定长度19字节
            ⚠️注意⚠️ "x,y,z"为位置坐标，数字间只能说英文逗号，以及不能有空格！
        
        ::: param :::
            TASK_NO: 任务号 (1-255)
            CMD_NO: 指令编码 (1-255)
            LOCATION: 位置信息 "x,y,z"
        
        ::: return :::
            packet: 更改位置指令报文
        """
        
        # 构建基础头部
        header = RESProtocol.HEADER.value
        pre_info = self._pack_pre_info(FrameType.COMMAND.value)

        # 任务号
        task_no = struct.pack('B', TASK_NO)
        print("[CAR] 任务号: ", task_no)
        
        # 指令编号
        cmd_no = struct.pack('B', 189)
        # cmd_no = b'\xbd' # 第189个命令，文档上面没写，不知道有什么用
        
        # 指令ID
        cmd = WorkCommand.UPDATE_CAR_COORDINATES.value
        # cmd = b'\x50'
        
        # 组合指令信息
        cmd_info = cmd_no + cmd

        #### 指令参数（32） ####
        # 位置数据
        location = tuple(map(int, LOCATION.split(',')))
        x, y, z = location[0], location[1], location[2]
        # 位置编码: 空占位(8位) | X(8位) | Y(8位) | Z(8位)
        position = struct.pack('!BBBB', 0, x, y, z)
        print(f"[CAR] 位置编码: {position}")

        # 组合数据部份
        payload = task_no + cmd_info + position

        # 计算数据报长度
        data_lenght = self._data_length(pre_info + payload)
        
        # 构建数据内容
        data_part = header + pre_info + payload + data_lenght
        
        # 计算CRC
        crc = self._calculate_crc(data_part)

        # 基础尾部字段
        footer = RESProtocol.FOOTER.value
        
        # 组合完整报文
        packet = data_part + crc + footer
        print(f"[CAR] 位置更改指令报文: {packet}")
        
        # 返回报文
        return packet
    
    # 确认执行任务报文
    def do_task(
            self,
            TASK_NO: int,
            SEGMENTS: list
            ) -> bytes:
        """
        [确认执行任务] - 发送完任务报文后，要发送次报文确认，穿梭车才会执行任务
            ⚠️注意⚠️ - [任务号] 和 [路径段列表] 必须和 [构建整体任务报文] 一致!

        ::: param :::
            TASK_NO: 任务号 (1-255)
            CMD_NO: 指令编码 (1-255)
            SEGMENTS: 路径段列表 [(x, y, z, action), ...]
        
        ::: return :::
            packet: 确认执行任务报文
        """
        # 构建基础头部
        header = RESProtocol.HEADER.value
        pre_info = self._pack_pre_info(FrameType.COMMAND.value)
        
        # 任务号
        task_no = struct.pack('B', TASK_NO)
        print("[CAR] 任务号: ", task_no)
        
        # 指令编号
        cmd_no = struct.pack('B', 44)
        
        # 指令ID
        cmd = ImmediateCommand.SET_SEGMENT_NO.value
        
        # 组合指令信息
        cmd_info = cmd_no + cmd
        
        #### 指令参数（32） ####
        # 计算动态长度: 4字节*段数
        segment_count = struct.pack('>I', self._segments_task_len(SEGMENTS))
        print("[CAR] 任务段数: ", segment_count)

        # 组合指令所有数据
        payload = task_no + cmd_info + segment_count
        
        # 计算数据段长度
        data_length = self._data_length(pre_info + payload)
        
        # 组合数据段
        data_part = header + pre_info + payload + data_length

        # 计算CRC
        crc = self._calculate_crc(data_part)
        
        # 基础尾部字段
        footer = RESProtocol.FOOTER.value

        # 组装报文
        packet = data_part + crc + footer
        print("[CAR] 任务确认报文: ", packet)

        # 返回报文
        return packet