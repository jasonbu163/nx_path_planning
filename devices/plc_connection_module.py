# /devices/plc_connection_module.py
from snap7.client import Client
from typing import Union
import asyncio

from .devices_logger import DevicesLogger

class PLCConnectionBase(DevicesLogger):
    """
    PLC连接模块
    """
    def __init__(self, HOST: str):
        """
        [初始化PLC连接模块]\n
        ::: param :::\n
            HOST: 服务器主机地址, 如 "192.168.8.30"
        """
        super().__init__(self.__class__.__name__)
        self._ip = HOST
        self.client = Client()
        self._connected = False

    
    #####################################################
    ####################### 同步方法 #####################
    #####################################################

    def connect(self) -> bool:
        """
        [同步连接PLC]
        """
        try:
            self.logger.info(f"🔌 正在连接到 PLC: {self._ip} (rack=0, slot=1)")
            self.client.connect(self._ip, 0, 1)  # 默认 rack=0, slot=1
            self._connected = self.client.get_connected()
            if self._connected:
                self.logger.info(f"✅ 成功连接 PLC：{self._ip}")
                return True
            else:
                self.logger.error("❌ PLC返回连接失败")
                return False
        except Exception as e:
            self.logger.error(f"❌ 连接失败：{e}", exc_info=True)
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        """
        [断开PLC连接]
        """
        if self._connected:
            self.client.disconnect()
            self._connected = False
            self.logger.info("⛔ PLC连接已关闭")
    
    def is_connected(self) -> bool:
        """
        [检查PLC是否已连接]
        """
        return self.client.get_connected()

    def read_db(self, db_number: int, start: int, size: int) -> bytes:
        """
        [按字节读取DB块信息] 读取指定 DB 块，从 start 偏移开始，长度为 size（单位：字节）\n
        ::: param :::\n
            db_number: DB块号\n
            start: 偏移量\n
            size: 字节数量
        ::: return :::
            返回DB块数据
        """
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        return self.client.db_read(db_number, start, size)

    def write_db(self, db_number: int, start: int, data: bytes) -> None:
        """
        [按字节写入DB块信息] 将 data 写入指定 DB 块的偏移位置\n
        ::: param :::\n
            db_number: DB块号\n
            start: 偏移量\n
            size: 字节数量
        """
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        self.client.db_write(db_number, start, data)
        self.logger.info(f"📤 写入 DB{db_number}[{start}] 成功，长度: {len(data)} bytes")

    def read_bit(self, db_number: int, offset: Union[float, int], size: int = 1) -> int:
        """
        [读取指定位的值]\n
        ::: param :::\n
            db_number: DB块编号\n
            offset: 偏移地址 (格式：字节.位 如 22.0)\n
            size: 读取位数 (默认为1位)\n
        ::: return :::\n
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
    
    def write_bit(self, db_number: int, offset: Union[float, int], value: Union[int, bool], size: int = 1) -> None:
        """
        [写入指定位的值]\n
        ::: param :::\n
            db_number: DB块编号\n
            offset: 偏移地址 (格式：字节.位 如 22.0)\n
            value: 要写入的值 (0/1或布尔值)\n
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

    
    #####################################################
    ####################### 异步方法 #####################
    #####################################################
    
    async def async_connect(self) -> bool:
        """
        [异步连接PLC]
        """
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.connect)
            if self._connected:
                self.logger.info(f"🔌 PLC连接状态: 已连接到 {self._ip}")
                return True
            else:
                self.logger.error("❌ 异步连接失败，未知原因")
                return False
        except Exception as e:
            self.logger.error(f"🚨 异步连接异常: {str(e)}", exc_info=True)
            return False

    async def async_disconnect(self) -> bool:
        """
        [断开PLC连接]
        """
        if self._connected:
            self.client.disconnect()
            self._connected = False
            self.logger.info("⛔ PLC连接已关闭")
        return True