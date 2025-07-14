# /devices/plc_service.py
from snap7.client import Client
import logging
from typing import Union

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class PLCService:
    def __init__(self, ip: str):
        self.ip = ip
        self.client = Client()
        self._connected = False

    def connect(self):
        try:
            self.client.connect(self.ip, 0, 1)  # 默认 rack=0, slot=1
            self._connected = self.client.get_connected()
            logger.info(f"✅ 成功连接 PLC：{self.ip}")
        except Exception as e:
            logger.error(f"❌ 连接失败：{e}")
            self._connected = False
            raise

    def is_connected(self) -> bool:
        return self.client.get_connected()

    def read_db(self, db_number: int, start: int, size: int) -> bytes:
        """读取指定 DB 块，从 start 偏移开始，长度为 size（单位：字节）"""
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        return self.client.db_read(db_number, start, size)

    def write_db(self, db_number: int, start: int, data: bytes) -> None:
        """将 data 写入指定 DB 块的偏移位置"""
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        self.client.db_write(db_number, start, data)
        logger.info(f"📤 写入 DB{db_number}[{start}] 成功，长度: {len(data)} bytes")

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
        logger.info(f"🔧 位写入成功 DB{db_number}[{offset}]: 值={value}")
