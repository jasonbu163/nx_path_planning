# /devices/plc_service_asyncio.py
from snap7.client import Client
import logging
import asyncio
from typing import Callable, Any, Union
import struct
import time

from .plc_enum import PLCAddress, FLOOR, TASK_TYPE
from res_protocol_system import PacketBuilder, PacketParser, RESProtocol
from map_core import PathCustom

# 整数计数器类，用于生成连续的整数
class IntCounter:
    def __init__(self):
        self.count = 0
        self.max_val = 255
    
    def __call__(self):
        self.count = (self.count % self.max_val) + 1
        time.sleep(1)
        return struct.pack('B', self.count)

# PLC设备服务类
class DevicesService:
    def __init__(self, plc_ip: str, car_ip: str, car_port: int):
        """
        初始化TCP客户端
        :param plc_ip: plc地址
        :param car_ip: 小车地址
        :param car_port: 小车端口
        """
        
        self.plc_ip = plc_ip
        self.client = Client()
        self._connected = False
        self._monitor_task = None  # 用于存储监控任务的引用
        self._stop_monitor = asyncio.Event()  # 停止监控的事件标志
        
        self.car_ip = car_ip
        self.car_port = car_port
        self.reader = None
        self.writer = None
        self.connected = False

        # 日志
        self.logger = self.setup_logger()
        
        # 创建地图实例
        self.map = PathCustom()

        # 生命周期
        self.counter = IntCounter()
        # 用来调crc和报文长度计算
        self.builder = PacketBuilder(2)
        # 解析报文
        self.parser = PacketParser()

    def setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger("Devices Service")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s -  %(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    ############# PLC的连接 和 基础读写 ######################
    async def async_connect(self):
        """异步连接PLC"""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.connect)
            if self._connected:
                self.logger.info(f"🔌 PLC连接状态: 已连接到 {self.plc_ip}")
            else:
                self.logger.error("❌ 异步连接失败，未知原因")
        except Exception as e:
            self.logger.error(f"🚨 异步连接异常: {str(e)}", exc_info=True)
            raise

    def connect(self):
        """同步连接PLC"""
        try:
            self.logger.info(f"🔌 正在连接到 PLC: {self.plc_ip} (rack=0, slot=1)")
            self.client.connect(self.plc_ip, 0, 1)  # 默认 rack=0, slot=1
            self._connected = self.client.get_connected()
            if self._connected:
                self.logger.info(f"✅ 成功连接 PLC：{self.plc_ip}")
            else:
                self.logger.error("❌ PLC返回连接失败")
        except Exception as e:
            self.logger.error(f"❌ 连接失败：{e}", exc_info=True)
            self._connected = False
            raise

    async def disconnect(self):
        """断开PLC连接"""
        if self._connected:
            self.client.disconnect()
            self._connected = False
            self.logger.info("⛔ PLC连接已关闭")
            
    def is_connected(self) -> bool:
        return self.client.get_connected()

    def read_db(self, db_number: int, start: int, size: int) -> bytes:
        """读取指定 DB 块"""
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        return self.client.db_read(db_number, start, size)

    def write_db(self, db_number: int, start: int, data: bytes) -> None:
        """写入指定 DB 块"""
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        self.client.db_write(db_number, start, data)
        self.logger.info(f"📤 写入 DB{db_number}[{start}] 成功，长度: {len(data)} bytes")

    ########################## 小车的连接 和 基础收发报文 ##########################

    async def car_connect(self):
        """
        连接到TCP服务器
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(self.car_ip, self.car_port)
            self.connected = True
            self.logger.info(f"[CLIENT] 已连接到服务器 {self.car_ip}:{self.car_port}")
        except ConnectionRefusedError:
            self.logger.info("[CLIENT] 无法连接到服务器")
            self.connected = False
        return self.connected
    
    async def car_send_message(self, message):
        """
        发送消息到服务器
        :param message: 要发送的消息内容
        """
        if not self.writer:
            return False
        
        self.writer.write(message)
        await self.writer.drain()
        self.logger.info(f"[CLIENT] 已发送: {message}")
        return True
    
    async def car_receive_message(self):
        """
        接收服务器响应
        :return: 服务器返回的消息
        """
        if not self.reader:
            return None
        
        data = await self.reader.read(1024)
        if not data:
            return None
        
        # response = data.decode()
        response = data
        self.logger.info(f"[CLIENT] 收到服务端回复: {response}")
        return response
    
    async def car_close(self):
        """
        关闭连接
        """
        if self.connected and self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.connected = False
            self.logger.info("[CLIENT] 连接已关闭")
        return True

    ########################## PLC的高级应用 #################################

    # def read_bit(self, db_number: int, byte_offset: float, bits: int = 1) -> int:
    #     """
    #     读取指定位或多位值
    #     :param byte_offset: 格式为 [字节号].[位号] (如 22.3 表示第22字节的第3位)
    #     :param bits: 要读取的位数(1-8)
    #     :return: 整数值(0~255)
    #     """
    #     if not self.is_connected():
    #         raise ConnectionError("未连接到PLC")
            
    #     # 分解字节地址和位偏移
    #     base_offset, bit_position = divmod(byte_offset, 1)
    #     base_offset = int(base_offset)
    #     bit_position = round(bit_position * 10)  # 将小数部分转换为位序号
        
    #     # 参数有效性检查
    #     if bit_position not in [0, 1, 2, 3, 4, 5, 6, 7]:
    #         raise ValueError("位偏移必须是0.0到7.7之间的数值")
    #     if not 1 <= bits <= 8:
    #         raise ValueError("读取位数必须在1-8之间")
    #     if bit_position + bits > 8:
    #         raise ValueError("读取范围超出单个字节边界")
            
    #     # 读取整个字节
    #     byte_data = self.read_db(db_number, base_offset, 1)
    #     current_byte = byte_data[0]  # 提取字节值
        
    #     # 创建位掩码并提取特定位
    #     mask = ((1 << bits) - 1) << bit_position
    #     extracted_bits = (current_byte & mask) >> bit_position
        
    #     return extracted_bits
    def read_bit(self, db_number: int, offset: Union[float, int], size: int = 1) -> int:
        """
        读取指定位的值
        Args:
            db_number: DB块编号
            offset: 偏移地址 (格式：字节.位 如 22.0)
            size: 读取位数 (默认为1位)
        Returns:
            读取到的位值（0/1）或多位值（当size>1时返回整数）
        """
        if not isinstance(offset, float) and '.' not in str(offset):
            raise ValueError("位偏移量必须使用float格式(如22.0)")
        
        byte_offset = int(offset)
        bit_offset = int(round((offset - byte_offset) * 10))
        
        # 验证位偏移范围
        if not 0 <= bit_offset <= 7:
            raise ValueError("位偏移必须在0-7范围内")
        
        # 读取包含目标位的整个字节
        data = self.read_db(db_number, byte_offset, 1)
        byte_value = data[0]
        
        # 提取指定位
        if size == 1:
            return (byte_value >> bit_offset) & 0x01
        else:
            # 提取多位值
            mask = (1 << size) - 1
            return (byte_value >> bit_offset) & mask
        
    # def write_bit(self, db_number: int, byte_offset: float, value: int, bits: int = 1) -> None:
    #     """
    #     写入指定位或多位值
    #     :param byte_offset: 格式为 [字节号].[位号] (如 22.3 表示第22字节的第3位)
    #     :param value: 要写入的整数值(0~255)
    #     :param bits: 要写入的位数(1-8)
    #     """
    #     if not self.is_connected():
    #         raise ConnectionError("未连接到PLC")
            
    #     # 分解字节地址和位偏移
    #     base_offset, bit_position = divmod(byte_offset, 1)
    #     base_offset = int(base_offset)
    #     bit_position = round(bit_position * 10)  # 将小数部分转换为位序号
        
    #     # 参数有效性检查
    #     if bit_position not in [0, 1, 2, 3, 4, 5, 6, 7]:
    #         raise ValueError("位偏移必须是0.0到7.7之间的数值")
    #     if not 1 <= bits <= 8:
    #         raise ValueError("写入位数必须在1-8之间")
    #     if bit_position + bits > 8:
    #         raise ValueError("写入范围超出单个字节边界")
    #     max_value = (1 << bits) - 1
    #     if value > max_value or value < 0:
    #         raise ValueError(f"写入值必须在0~{max_value}之间")
            
    #     # 读取当前字节状态
    #     byte_data = self.read_db(db_number, base_offset, 1)
    #     current_byte = byte_data[0]
        
    #     # 创建位掩码和更新值
    #     mask = ((1 << bits) - 1) << bit_position
    #     value_to_write = (value << bit_position) & mask
    #     updated_byte = (current_byte & ~mask) | value_to_write
        
    #     # 写入更新后的字节
    #     self.write_db(db_number, base_offset, bytes([updated_byte]))
    #     logger.info(f"📝 DB{db_number}[{base_offset}.{bit_position}]写入{bits}位成功: 0x{value:02X}")

    def write_bit(self, db_number: int, offset: Union[float, int], value: Union[int, bool], size: int = 1) -> None:
        """
        写入指定位的值
        Args:
            db_number: DB块编号
            offset: 偏移地址 (格式：字节.位 如 22.0)
            value: 要写入的值 (0/1或布尔值)
            size: 写入位数 (默认为1位)
        """
        if not isinstance(offset, float) and '.' not in str(offset):
            raise ValueError("位偏移量必须使用float格式(如22.0)")
            
        byte_offset = int(offset)
        bit_offset = int(round((offset - byte_offset) * 10))
        
        # 验证位偏移范围
        if not 0 <= bit_offset <= 7:
            raise ValueError("位偏移必须在0-7范围内")
            
        if size > (8 - bit_offset):
            raise ValueError("请求位数超出字节边界")
        
        # 读取当前字节值
        current_data = self.read_db(db_number, byte_offset, 1)
        current_value = current_data[0]
        
        # 创建位掩码
        mask = (1 << size) - 1
        clear_mask = ~(mask << bit_offset)
        
        # 转换为整数
        if isinstance(value, bool):
            value = 1 if value else 0
        
        # 验证取值范围
        if value < 0 or value >= (1 << size):
            raise ValueError(f"值必须介于0和{(1 << size) - 1}之间")
        
        # 更新字节值
        new_value = (current_value & clear_mask) | (value << bit_offset)
        
        # 写回PLC
        self.write_db(db_number, byte_offset, bytes([new_value]))
        self.logger.info(f"🔧 位写入成功 DB{db_number}[{offset}]: 值={value}")

    
    async def monitor_condition(
        self,
        monitor_db: int,
        monitor_offset: float,
        bits: int,
        target_value: int,
        callback: Callable[[], Any],
        poll_interval: float = 0.5
    ):
        """
        监控PLC状态并执行回调
        :param monitor_db: 监控的DB块号
        :param monitor_offset: 监控的地址偏移
        :param bits: 监控的位数
        :param target_value: 要匹配的目标值
        :param callback: 条件满足时的回调函数
        :param poll_interval: 轮询间隔(秒)
        """
        try:
            self.logger.info(f"🔍 启动PLC监控: DB{monitor_db}[{monitor_offset}] {bits}位 == 0x{target_value:02X}")
            
            while not self._stop_monitor.is_set():
                # 异步读取PLC状态
                try:
                    current_value = await asyncio.to_thread(
                        self.read_bit, monitor_db, monitor_offset, bits
                    )
                except Exception as e:
                    self.logger.error(f"读取PLC状态失败: {e}")
                    await asyncio.sleep(poll_interval)
                    continue
                
                # 检查条件是否满足
                if current_value == target_value:
                    self.logger.info("🎯 条件满足! 执行回调函数")
                    try:
                        # 执行回调函数
                        if asyncio.iscoroutinefunction(callback):
                            await callback()
                        else:
                            await asyncio.to_thread(callback)
                        self.logger.info("✅ 回调执行完成")
                        return
                    except Exception as e:
                        self.logger.error(f"回调执行失败: {e}")
                        return
                
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            self.logger.info("⏹️ 监控任务已取消")
        finally:
            self._stop_monitor.clear()

    async def start_monitoring(
        self,
        monitor_db: int,
        monitor_offset: float,
        bits: int,
        target_value: int,
        callback: Callable[[], Any],
        poll_interval: float = 0.5
    ):
        """启动监控任务"""
        # 停止现有监控任务
        await self.stop_monitoring()
        
        # 创建新监控任务
        self._monitor_task = asyncio.create_task(
            self.monitor_condition(
                monitor_db, monitor_offset, bits, target_value, callback, poll_interval
            )
        )
        return self._monitor_task

    async def stop_monitoring(self):
        """停止监控任务"""
        if self._monitor_task and not self._monitor_task.done():
            self._stop_monitor.set()
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            finally:
                self._monitor_task = None

    # 等待PLC动作完成的超时时间（秒）
    ACTION_TIMEOUT = 30.0

    async def wait_for_bit_change(self, db_number, address, target_value, timeout=ACTION_TIMEOUT):
        """等待PLC指定的位状态变化为目标值"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 读取当前值
            # Address = f"{byte_offset}.{bit_offset}"
            current_value = await asyncio.to_thread(self.read_bit, db_number, address, 1)
            
            if current_value == target_value:
                # self.logger.info(f"✅ PLC动作完成: DB{db_number}[{byte_offset}.{bit_offset}] == {target_value}")
                self.logger.info(f"✅ PLC动作完成: DB{db_number}[{address}] == {target_value}")
                return True
                
            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                self.logger.info(f"❌ 超时错误: 等待PLC动作超时 ({timeout}s)")
                return False
                
            # 等待一段时间再次检查
            await asyncio.sleep(0.5)

    ################### 小车的高级应用 #####################

    def _pack_pre_info(self, frame_type):
        """
        构建报文前段信息
        格式: 报文版本(4bit) 报文类型(4bit)
        """
        version_type = (RESProtocol.VERSION << 4) | (frame_type & 0x0F)
        return struct.pack('!B',version_type)
    
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

    # 心跳报文
    def heartbeat(self):
        header = RESProtocol.HEADER
        device_id = struct.pack('B', 2)
        message = b'\x10\x00\x0b'
        footer = RESProtocol.FOOTER
        data = header + device_id + self.counter() + message
        crc = self.builder._calculate_crc(data)
        packet = data + crc + footer
        return packet
    # 心跳报文使用实例
    # self.logger.info(heartbeat())
    # self.logger.info(message)
    # for i in range(257):
    #     # self.logger.info(counter())  # 输出1-256，然后回到1
    #     data = header + device_id + counter() + message
    #     crc = builder._calculate_crc(data)
    #     packet = data + crc + footer
    #     self.logger.info(packet)

    # 更换位置指令报文
    def location_change(self, location):
        """
        构建调试指令报文
        固定长度19字节
        :param cmd_id: (x, y, z)
        :return: 调试指令报文
        """
        
        # 构建基础头部
        header = RESProtocol.HEADER
        device_id = struct.pack('B', 2)
        life = self.counter()
        packet_info = self._pack_pre_info(RESProtocol.FrameType.COMMAND)

        # 调试指令信息
        # task_no = 2
        # cmd_no = 189
        # cmd = 80
        # cmd_info = struct.pack('!BBB', task_no, cmd_no, cmd)
        cmd_info = b'\x02\xbd\x50'

        location = tuple(map(int, location.split(',')))
        # 位置数据
        x, y, z = location[0], location[1], location[2]
        # 位置编码: X(8位) | Y(8位) | Z(8位) | 动作(8位)
        position = struct.pack('!BBBB', 0, x, y, z)
        self.logger.info("位置编码: ", position)

        # 组合数据部份
        payload = cmd_info + position
        
        # 构建数据内容
        data_part = header + device_id + life + packet_info + payload + self.builder._data_length(device_id + life + packet_info + payload)
        
        # 计算CRC
        crc = self.builder._calculate_crc(data_part)

        # 基础尾部字段
        footer = RESProtocol.FOOTER
        
        # 组合完整报文
        packet = data_part + crc + footer
        self.logger.info("[发送] 调试指令报文: ", packet)
        
        # 返回报文
        return packet

    # 任务报文
    def build_task(self, task_no, segments):
        """
        构建整体任务报文
        :param task_no: 任务序号 (1-255)
        :param segments: 路径段列表 [(x, y, z, action), ...]
        :return: 任务报文
        """
        # 构建基础头部
        header = b'\x02\xfd'
        device_id = struct.pack('B', 2)
        life = self.counter()
        packet_info = self._pack_pre_info(RESProtocol.FrameType.TASK)
        
        # 构建数据内容
        # 计算动态长度: 4字节*段数
        segment_count = self.segments_task_len(segments)
        self.logger.info("创建 任务序号: ", task_no)
        self.logger.info("创建 任务段数: ", segment_count)
        # 添加任务数据
        payload = struct.pack('!BB', task_no, segment_count)
        # 添加路径段
        for segment in segments:
            x, y, z, action = segment
            # 位置编码: X(8位) | Y(8位) | Z(8位) | 动作(8位)
            # position = (x << 24) | (y << 16) | (z << 8) | action
            # self.logger.info("位置编码: ", hex(position))
            # payload += struct.pack('!I', position)
            position = struct.pack('!BBBB', x, y, z, action)
            self.logger.info("位置编码: ", position)
            payload += position
        
        # 计算数据段长度
        data_length = self.builder._data_length(device_id + life + packet_info + payload)
        
        # 组合数据段
        data_part = header + device_id + life + packet_info + payload + data_length

        # 计算CRC
        crc = self.builder._calculate_crc(data_part)
        
        # 基础尾部字段
        footer = RESProtocol.FOOTER

        # 组装报文
        packet = data_part + crc + footer
        self.logger.info("[发送] 整体任务报文: ", packet)

        # 返回报文
        return packet

    # 确认执行任务报文
    def do_task(self, task_no, segments):
        """
        构建整体任务报文
        :param task_no: 任务序号 (1-255)
        :param segments: 路径段列表 [(x, y, z, action), ...]
        :return: 任务报文
        """
        # 构建基础头部
        header = RESProtocol.HEADER
        device_id = struct.pack('B', 2)
        life = self.counter()
        packet_info = self._pack_pre_info(RESProtocol.FrameType.COMMAND)
        
        # 构建数据内容
        # 任务号
        task_no = struct.pack('B', task_no)
        cmd_no = 44
        cmd = 144
        cmd_info = struct.pack('!BB', cmd_no, cmd)
        # 计算动态长度: 4字节*段数
        segment_count = struct.pack('>I', self.segments_task_len(segments))
        
        self.logger.info("发送 任务序号: ", task_no)
        self.logger.info("发送 任务段数: ", segment_count)

        payload = task_no + cmd_info + segment_count
        
        # 计算数据段长度
        data_length = self.builder._data_length(device_id + life + packet_info + payload)
        
        # 组合数据段
        data_part = header + device_id + life + packet_info + payload + data_length

        # 计算CRC
        crc = self.builder._calculate_crc(data_part)
        
        # 基础尾部字段
        footer = RESProtocol.FOOTER

        # 组装报文
        packet = data_part + crc + footer
        self.logger.info("[发送] 整体任务报文: ", packet)

        # 返回报文
        return packet
    
    # 心跳报文
    async def send_heartbeat(self, time: int):
        """
        :param time: 心跳次数
        """
        for i in range(time):
            packet = self.heartbeat()
            if await self.car_connect():
                await self.car_send_message(packet)
                response = await self.car_receive_message()
                if response:
                    msg = self.parser.parse_heartbeat_response(response)
                    self.logger.info(msg)
                    await self.car_close()
        return msg
    
    # 修改小车位置
    async def change_car_location(self, car_location):
        """
        :param car_location: 小车位置 如，"6,3,1"
        """
        packet = self.location_change(car_location)
        self.logger.info(packet)
        if await self.car_connect():
            await self.car_send_message(packet)
            response = await self.car_receive_message()
            self.logger.info(response)
            if response:
                # msg = parser.parse_heartbeat_response(response)
                # print(msg)
                await self.car_close()
                return "位置修改成功"
        return "位置修改失败"

    # 获取小车位置
    async def car_current_location(self, times: int):
        """
        获取小车位置
        :param times: 心跳次数
        :return: 小车当前位置
        例如: "6,3,1"
        """
        # 发送
        heartbeat_msg = await self.send_heartbeat(times)
        car_current_location = heartbeat_msg['current_location']
        car_current_location = f"{car_current_location[0]},{car_current_location[1]},{car_current_location[2]}"
        return car_current_location
    

    # 发送小车移动任务
    async def car_move(self, target):
        """
        :param target: 小车移动目标 如，"6,3,1"
        """
        # 创建任务号
        import random
        task_no = random.randint(1, 100)

        # 获取小车当前坐标
        heartbeat_msg = await self.send_heartbeat(1)
        car_current_location = heartbeat_msg['current_location']
        car_current_location = f"{car_current_location[0]},{car_current_location[1]},{car_current_location[2]}"
        
        # 创建移动路径
        # segments = [
        #     (6,3,1,0),
        #     (4,3,1,5),
        #     (4,1,1,6),
        #     (1,1,1,0)
        #             ]
        segments = self.map.build_segments(car_current_location, target)
        # print(segments)

        # 发送任务报文
        task_packet = self.build_task(task_no, segments)
        if await self.car_connect():
            await self.car_send_message(task_packet)
            response = await self.car_receive_message()
            if response:
                # msg = parser.parse_task_response(response)
                # print(msg)
                # 发送任务确认执行报文
                do_packet = self.do_task(task_no, segments)
                await self.car_send_message(do_packet)
                response = await self.car_receive_message()
                if response:
                    # msg = parser.parse_task_response(response)
                    # self.logger.info(msg)
                    await self.car_close()

    def add_pick_drop_actions(self, point_list):
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


    # 发送移动货物任务
    async def good_move(self, target):
        """
        :param target: 小车移动目标 如，(6,3,1)
        """
        # 创建任务号
        import random
        task_no = random.randint(1, 100)

        # 获取小车当前坐标
        heartbeat_msg = await self.send_heartbeat(1)
        car_current_location = heartbeat_msg['current_location']
        car_current_location = f"{car_current_location[0]},{car_current_location[1]},{car_current_location[2]}"
        
        # 创建移动路径
        # segments = [
        #     (6,3,1,0),
        #     (4,3,1,5),
        #     (4,1,1,6),
        #     (1,1,1,0)
        #             ]
        segments = self.map.build_segments(car_current_location, target)
        segments = self.add_pick_drop_actions(segments)
        # print(segments)

        # 发送任务报文
        task_packet = self.build_task(task_no, segments)
        if await self.car_connect():
            await self.car_send_message(task_packet)
            response = await self.car_receive_message()
            if response:
                # msg = parser.parse_task_response(response)
                # print(msg)
                # 发送任务确认执行报文
                do_packet = self.do_task(task_no, segments)
                await self.car_send_message(do_packet)
                response = await self.car_receive_message()
                if response:
                    # msg = parser.parse_task_response(response)
                    # print(msg)
                    await self.car_close()

    ############# PLC联合小车的业务动作 #######################

    # 二进制字符串转字节码
    def binary2bytes(self, binary_str):
        value = int(binary_str, 2)
        return struct.pack('!B', value)

    # 获得提升机所在层
    def get_lift(self):
        # 读取提升机所在层
        db = self.read_db(11, PLCAddress.CURRENT_LAYER.value, 2)
        # return struct.unpack('!H', db)[0]
        return db
    
    # 移动提升机
    def lift_move(self, task_type, task_num, end_floor):
        task_type = struct.pack('!H', task_type)
        task_num = struct.pack('!H', task_num)
        # start_floor = struct.pack('!H', start_floor)
        # start_floor = self.get_lift()
        end_floor = struct.pack('!H', end_floor)

        # 任务类型
        self.write_db(12, 0, task_type)
        # 任务号
        self.write_db(12, 6, task_num)
        # 起始层
        # self.write_db(12, start=2, data=start_floor)
        # 目标层
        self.write_db(12, start=4, data=end_floor)
        # 读取提升机是否空闲
        if self.read_bit(11, PLCAddress.IDLE.value):
            self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

    
    # 入库到提升机
    def inband(self):
        self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

        # 放料完成（启动）
        self.write_bit(12, PLCAddress.FEED_COMPLETE_1010.value, 1)
        if self.read_bit(12, PLCAddress.FEED_COMPLETE_1010.value) == 1:
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1010.value, 0)

        # 进入到提升机
        lift_code = struct.pack('!H', FLOOR.LIFT)
        time.sleep(1)
        self.write_db(12, PLCAddress.TARGET_1010.value, lift_code)
        if self.read_db(12, PLCAddress.TARGET_1010.value, 2) == lift_code:
            self.write_db(12, PLCAddress.TARGET_1010.value, b'\x00\x00')
    
    # 从提升机出库
    def outband(self):
        # 告诉PLC目标层到达
        self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

        # 写入出库
        data = struct.pack('!H', FLOOR.GATE)
        time.sleep(1)
        self.write_db(12, PLCAddress.TARGET_1020.value, data)
        time.sleep(1)
        if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
            self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')

        # 清除目标到达信号
        if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
            self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

    # 楼层进入提升机
    def floor_to_lift(self, floor):
        """
        param floor: 楼层 int
        """
        # 楼层1
        if floor == 1:
            # 放料进行中
            self.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1030.value, 1)
            # 等待小车送货到提升机 -> 联动小车
            # time.sleep(30)
            # 放料完成
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 1)
            if self.read_bit(12, PLCAddress.FEED_COMPLETE_1030.value) == 1:
                self.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 0)
            # 货物送入提升机
            # data = struct.pack('!H', FLOOR.LIFT)
            # self.write_db(12, PLCAddress.TARGET_1030.value, data)
            # if self.read_db(12, PLCAddress.TARGET_1030.value, 1) == data:
            #     self.write_db(12, PLCAddress.TARGET_1030.value, b'\x00\x00')

        # 楼层2
        elif floor == 2:
            # 放料进行中
            self.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1040.value, 1)
            # # 等待小车送货到提升机 -> 联动小车
            # # time.sleep(30)
            # 放料完成
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1040.value, 1)
            if self.read_bit(12, PLCAddress.FEED_COMPLETE_1040.value) == 1:
                self.write_bit(12, PLCAddress.FEED_COMPLETE_1040.value, 0)
            # 货物送入提升机
            # data = struct.pack('!H', FLOOR.LIFT)
            # self.write_db(12, PLCAddress.TARGET_1040.value, data)
            # if self.read_db(12, PLCAddress.TARGET_1040.value, 1) == data:
            #     self.write_db(12, PLCAddress.TARGET_1040.value, b'\x00\x00')
        
        # 楼层3
        elif floor == 3:
            # 放料进行中
            self.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1050.value, 1)
            # # 等待小车送货到提升机 -> 联动小车
            # # time.sleep(30)
            # 放料完成
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1050.value, 1)
            if self.read_bit(12, PLCAddress.FEED_COMPLETE_1050.value) == 1:
                self.write_bit(12, PLCAddress.FEED_COMPLETE_1050.value, 0)
            # 货物送入提升机
            # data = struct.pack('!H', FLOOR.LIFT)
            # self.write_db(12, PLCAddress.TARGET_1050.value, data)
            # if self.read_db(12, PLCAddress.TARGET_1050.value, 1) == data:
            #     self.write_db(12, PLCAddress.TARGET_1050.value, b'\x00\x00')
        
        # 楼层4
        elif floor == 4:
            # # 放料进行中
            self.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1060.value, 1)
            # # 等待小车送货到提升机 -> 联动小车
            # # time.sleep(30)
            # # 放料完成
            self.write_bit(12, PLCAddress.FEED_COMPLETE_1060.value, 1)
            if self.read_bit(12, PLCAddress.FEED_COMPLETE_1060.value) == 1:
                self.write_bit(12, PLCAddress.FEED_COMPLETE_1060.value, 0)
            # 货物送入提升机
            # data = struct.pack('!H', FLOOR.LIFT)
            # self.write_db(12, PLCAddress.TARGET_1060.value, data)
            # if self.read_db(12, PLCAddress.TARGET_1060.value, 1) == data:
            #     self.write_db(12, PLCAddress.TARGET_1060.value, b'\x00\x00')
        
        else:
            self.logger.info("无效的楼层")
        

    def lift_to_everylayer(self, target_floor):
        """
        :::param target_floor: 目标楼层
        """
        # 确认提升机
        self.logger.info(f"确认提升机状态: {self.read_bit(11, PLCAddress.PLATFORM_PALLET_READY_1020.value)}")

        # 确认目标层到达
        time.sleep(1)
        self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)

        time.sleep(0.5)
        # 移动到1层
        if target_floor == 1:
            data = struct.pack('!H', FLOOR.LAYER_1)
            self.write_db(12, PLCAddress.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
            # 到达目标层状态 清零
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
        
        # 移动到2层
        elif target_floor == 2:
            data = struct.pack('!H', FLOOR.LAYER_2)
            self.write_db(12, PLCAddress.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
            # 到达目标层状态 清零
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
        
        # 移动到3层
        elif target_floor == 3:
            data = struct.pack('!H', FLOOR.LAYER_3)
            self.write_db(12, PLCAddress.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
            # 到达目标层状态 清零
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

        # 移动到4层
        elif target_floor == 4:
            data = struct.pack('!H', FLOOR.LAYER_4)
            self.write_db(12, PLCAddress.TARGET_1020.value, data)
            time.sleep(2)
            # 清零
            if self.read_db(12, PLCAddress.TARGET_1020.value, 2) == data:
                self.write_db(12, PLCAddress.TARGET_1020.value, b'\x00\x00')
            # 到达目标层状态 清零
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

        else:
            raise ValueError("Invalid target floor")

    # 小车换层
    async def car_cross_layer(self, target_location: str):
        """
        穿梭车跨层
        :::param traget_location: 目标位置 如 "6,3,1"
        """
        # 获取小车坐标
        car_location =  await self.car_current_location(1)
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_cur_loc = list(map(int, car_location.split(',')))
        car_current_floor = car_cur_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_current_floor}")
        
        # 获取目标位置坐标 
        self.logger.info(f"🧭 穿梭车目的坐标: {target_location}")
        target_loc = list(map(int, target_location.split(',')))
        traget_floor = target_loc[2]
        self.logger.info(f"🧭 穿梭车目的楼层: {traget_floor}")




        self.logger.info("🚚 移动空载电梯到小车楼层...")
        # 提升机到达小车所在层
        # 随机生成个3位整数整数任务号
        import random
        task_num = random.randint(100, 999)
        if traget_floor != car_current_floor:
            self.lift_move(TASK_TYPE.IDEL, task_num, car_current_floor)
            # 等待电梯到达楼层 读取电梯是否空闲
            await self.wait_for_bit_change(11, 13.3, 1)
        # # 空载校准
        # elif traget_floor == car_current_floor:
        #     self.lift_move(TASK_TYPE.IDEL, task_num, car_current_floor)
        #     # 等待电梯到达楼层 读取电梯是否空闲
        #     await self.wait_for_bit_change(11, 13.3, 1)
        else:
            pass

        # 小车 进入 提升机
        # car_move(car_location, [6, 3, car_current_floor])
        self.logger.info("⏳ ！！！人工操作小车移动！！！")
        self.logger.info("⏳ 等待小车动作完成...")
        finish = input("人工确认小车进入提升机, 完成请输入(ok):")
        if finish == "ok":
            self.logger.info("人工确认小车动作完成！！")
        
        # 提升机到达目标层
        self.lift_move(TASK_TYPE.CAR, task_num+1, traget_floor)

        # 小车 离开 提升机
        # 等待电梯到达楼层 读取电梯是否空闲
        await self.wait_for_bit_change(11, 13.3, 1)
        # 修改小车楼层
        # car_location_change([6, 3, traget_floor])
        # car_move([6, 3, traget_floor], [5, 3, target_floor])
        self.logger.info("⏳ ！！！人工操作小车移动！！！")
        self.logger.info("⏳ 等待小车动作完成...")
        finish = input("人工确认小车进入提升机, 完成请输入(ok):")
        if finish == "ok":
            self.logger.info("人工确认小车动作完成！！")