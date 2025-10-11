# /devices/plc_connection_module.py
import time
from typing import Union, Callable, Any
import logging
logger = logging.getLogger(__name__)

from snap7.client import Client
from snap7.util import get_bool, set_bool, get_int, set_int

# from app.utils.devices_logger import DevicesLogger
from app.core.config import settings
from ..enum import DB_2, DB_11

class ConnectionBase():
    """PLC连接模块，基于同步通讯基础版"""
    def __init__(self, host: str):
        """初始化PLC连接模块

        Args:
            host: 服务器主机地址, 如 "192.168.8.30"
        """
        # super().__init__(self.__class__.__name__)
        self._ip = host
        self.client = Client()
        self._connected = False

    def connect(self, retry_count: int = 3, retry_interval: float = 2.0) -> bool:
        """同步连接PLC"""
        # 双重检查连接状态
        if self._connected and self.client.get_connected():
            logger.info("✅ 连接已存在，无需重新连接")
            return True
        
        # 如果已有连接但状态不一致，先断开
        if self._connected or self.client.get_connected():
            logger.warning("⚠️ 连接状态不一致，先关闭现有连接")
            self.client.disconnect()

        for attempt in range(1, retry_count + 1):
            try:
                logger.info(f"🔌 正在连接到 PLC: {self._ip} (rack=0, slot=1)")
                logger.info(f"⌛️ 尝试连接 {attempt}/{retry_count} {self._ip}")
                
                # 创建新的Client实例（避免重用问题连接）
                self.client = Client()
                
                # 尝试连接
                self.client.connect(self._ip, 0, 1)  # 默认 rack=0, slot=1
                self._connected = self.client.get_connected()

                if not self._connected:
                    logger.error("❌ PLC返回连接失败")
                    continue

                try:
                    # 读取一个测试值验证连接
                    data = self.client.get_cpu_info()
                    logger.debug(f"✉️ 读取CPU信息数据: {data}")
                except Exception as test_e:
                    logger.error(f"❌ 连接验证失败: {test_e}")
                    self._connected = False
                    continue
                
                logger.info(f"✅ 成功连接PLC: {self._ip}")
                return True
            
            except Exception as e:
                logger.error(f"❌ PLC连接失败({attempt}/{retry_count}): {str(e)}", exc_info=True)
                self._connected = False

                # 清理（如果连接部分成功）
                try:
                    self.client.disconnect()
                except:
                    pass
                
                # 等待（最后一次尝试不等待）
                if attempt < retry_count:
                    time.sleep(retry_interval)

        self._connected = False
        return False
    
    def disconnect(self) -> bool:
        """断开PLC连接"""
        # 如果未连接，直接返回成功
        if not self._connected and not self.client.get_connected():        
            logger.info(f"⚠️ PLC连接已断开, 无需操作")
            return True
        
        try:
            # 尝试断开连接
            self.client.disconnect()
            logger.info(f"⛓️‍💥 PLC已断开连接")
            return True
        except Exception as e:
            logger.error(f"❌ 断开连接失败: {e}", exc_info=True)
            return False
        finally:
            # 无论成功与否，更新状态
            self._connected = False
            # 重置客户端实例
            self.client = Client()
    
    def is_connected(self) -> bool:
        """检查PLC是否已连接"""
        return self.client.get_connected() and self._connected

    def read_db(self, db_number: int, start: int, size: int) -> bytes:
        """[按字节读取DB块信息] 读取指定 DB 块，从 start 偏移开始，长度为 size（单位：字节）
        
        Args:
            db_number: DB块号
            start: 偏移量
            size: 字节数量

        Returns:
            bytes: 返回DB块数据
        """
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        return self.client.db_read(db_number, start, size)

    def write_db(self, db_number: int, start: int, data: bytes) -> None:
        """[按字节写入DB块信息] 将 data 写入指定 DB 块的偏移位置

        Args:
            db_number: DB块号
            start: 偏移量
            size: 字节数量
        """
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        self.client.db_write(db_number, start, data)
        logger.debug(f"📤 写入 DB{db_number}[{start}] 成功，长度: {len(data)} bytes")

    def read_bit(self, db_number: int, offset: Union[float, int], size: int = 1) -> int:
        """读取指定位的值

        Args:
            db_number: DB块编号
            offset: 偏移地址 (格式：字节.位 如 22.0)
            size: 读取位数 (默认为1位)
        
        Returns:
            int: 读取到的位值（0/1）或多位值（当size>1时返回整数）
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
        """写入指定位的值
    
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
        logger.debug(f"🔧 位写入成功 DB{db_number}[{offset}]: 值={value}")

    def wait_for_bit_change(
            self,
            DB_NUMBER: int,
            ADDRESS: float,
            TRAGET_VALUE: int,
            TIMEOUT: float = settings.PLC_ACTION_TIMEOUT
            ) -> bool:
        """[同步] 等待PLC指定的位状态变化为目标值
        
        Args:
            DB_NUMBER: DB块号 
            ADDRESS: 位地址 
            TRAGET_VALUE: 目标值 
            TIMEOUT: 超时时间（秒）
        """
        time.sleep(2)
        start_time = time.time()
        
        while True:
            # 读取当前值
            current_value = self.read_bit(DB_NUMBER, ADDRESS, 1)
            
            if current_value == TRAGET_VALUE:
                logger.info(f"✅ PLC动作完成: DB{DB_NUMBER}[{ADDRESS}] == {TRAGET_VALUE}")
                return True
                
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > TIMEOUT:
                logger.error(f"❌ 超时错误: 等待PLC动作超时 ({TIMEOUT}s)")
                return False
                
            # 等待一段时间再次检查
            time.sleep(0.5)

class Connection():
    """PLC连接基类，改良版"""
    def __init__(self, host: str):
        """初始化PLC连接。
        
        Args:
            host: PLC IP地址
        """
        # super().__init__(self.__class__.__name__)
        self._ip = host
        self._rack = 0
        self._slot = 1

        self._client = Client()
        self._connected = False

    def connect(self, retry_count: int = 3, retry_interval: float = 2.0) -> bool:
        """[同步] 连接PLC
        
        Args:
            retry_count: 重试次数。默认3次
            retry_interval: 重试间隔时间。默认2秒
        
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        # 双重检查连接状态
        if self._connected and self.client.get_connected():
            logger.info("✅ 连接已存在，无需重新连接")
            return True
        
        # 如果已有连接但状态不一致，先断开
        if self._connected or self.client.get_connected():
            logger.warning("⚠️ 连接状态不一致，先关闭现有连接")
            self.client.disconnect()

        for attempt in range(1, retry_count + 1):
            try:
                logger.info(f"🔌 正在连接到PLC: Host-{self._ip} Rack-{self._rack} Slot-{self._slot}")
                logger.info(f"⌛️ 尝试连接({attempt}/{retry_count}): {self._ip}")
                
                # 创建新的Client实例（避免重用问题连接）
                self.client = Client()
                
                # 尝试连接
                self.client.connect(self._ip, self._rack, self._slot)
                self._connected = self.client.get_connected()

                if not self._connected:
                    logger.error("❌ PLC返回连接失败")
                    continue

                try:
                    # 读取一个测试值验证连接
                    data = self.client.get_cpu_info()
                    logger.debug(f"✉️ 读取CPU信息数据: {data}")
                except Exception as test_e:
                    logger.error(f"❌ 连接验证失败: {test_e}")
                    self._connected = False
                    continue
                
                logger.info(f"✅ 成功连接PLC: {self._ip}")
                return True
            
            except Exception as e:
                logger.error(f"❌ PLC连接失败({attempt}/{retry_count}): {str(e)}", exc_info=True)
                self._connected = False

                # 清理（如果连接部分成功）
                try:
                    self.client.disconnect()
                except:
                    pass
                
                # 等待（最后一次尝试不等待）
                if attempt < retry_count:
                    time.sleep(retry_interval)

        self._connected = False
        return False
    
    def disconnect(self) -> bool:
        """断开PLC连接
        
        Returns:
            bool: 断开成功返回True，否则返回False
        """
        # 如果未连接，直接返回成功
        if not self._connected and not self.client.get_connected():        
            logger.info(f"⚠️ PLC连接已断开, 无需操作")
            return True
        
        try:
            # 尝试断开连接
            self.client.disconnect()
            logger.info(f"⛓️‍💥 PLC已断开连接")
            return True
        except Exception as e:
            logger.error(f"❌ 断开连接失败: {e}", exc_info=True)
            return False
        finally:
            # 无论成功与否，更新状态
            self._connected = False
            # 重置客户端实例
            self.client = Client()

    def read_db(self, db_number: int, start: int, size: int) -> bytearray:
        """使用 snap7.client.Client 读取DB块数据
        
        Args:
            db_number: DB块编号
            start: 起始字节索引
            size: 读取字节数量
        
        Returns:
            bytearray: 读取到的数据
        """
        return self.client.db_read(db_number, start, size)
    
    def write_db(self, db_number: int, start: int, data: bytes) -> bool:
        """使用 snap7.client.Client 写入DB块数据
        
        Args:
            db_number: DB块编号
            start: 起始字节索引
            data: 要写入的数据
        
        Returns:
            bool: 写入成功返回True，否则返回False
        """
        self.client.db_write(db_number, start, data)

        size = len(data)
        flag = self.read_db(db_number, start, size)
        if flag == data:
            logger.debug(f"✅ 写入 DB{db_number}@{start} 成功，长度: {size} bytes")
            return True
        else:
            logger.error(f"❌ 写入 DB{db_number}@{start} 失败")
            return False

    def read_bit(self, db_number: int, byte_address: int, bit_address: int) -> bool:
        """使用 snap7.util 读取一个位（标准写法）

        Args:
            db_number: DB块编号
            byte_address: 字节地址。如 22
            bit_address: 位地址(0-7)。如 0

        Returns:
            bool: 位的布尔值
        """
        # 读取包含目标位的一个字节
        data = self.client.db_read(db_number, byte_address, 1)
        # 使用 get_bool 解析指定位
        return get_bool(data, 0, bit_address)  # 注意：这里的字节偏移是相对于data的0

    def write_bit(self, db_number: int, byte_address: int, bit_address: int, value: bool) -> bool:
        """使用 snap7.util 写入一个位（标准写法）

        Args:
            db_number: DB块编号
            byte_address: 字节地址。如 22
            bit_address: 位地址(0-7)。如 0
            value: 要写入的值

        Returns:
            bool: 成功写入返回True，否则返回False
        """
        # 读取包含目标位的一个字节
        data = self.client.db_read(db_number, byte_address, 1)
        # 使用 set_bool 修改指定位
        set_bool(data, 0, bit_address, value)  # 注意：这里的字节偏移是相对于data的0
        # 将修改后的整个字节写回
        self.client.db_write(db_number, byte_address, data)

        flag = self.read_bit(db_number, byte_address, bit_address)
        if flag == value:
            logger.debug(f"✅ 写入BD块的位成功 - DB{db_number}@{byte_address}.{bit_address} = {value}")
            return True
        else:
            logger.error(f"❌ 写入BD块的位失败")
            return False
        
    def read_int(self, db_number: int, start: int) -> int:
        """使用 snap7.util 读取一个整数（标准写法）
        
        Args:
            db_number: DB块编号
            start: 起始字节索引
        
        Returns:
            int: 读取到的整数值
        """
        data = self.client.db_read(db_number, start, 2)
        return get_int(data, 0)
    
    def write_int(self, db_number: int, start: int, value: int) -> bool:
        """使用 snap7.util 写入一个整数（标准写法）
        
        Args:
            db_number: DB块编号
            start: 起始字节索引
            value: 要写入的整数值
        
        Returns:
            bool: 写入成功返回True，否则返回False
        """
        data = self.client.db_read(db_number, start, 2)
        set_int(data, 0, value)
        self.client.db_write(db_number, start, data)

        flag = self.read_int(db_number, start)
        if flag == value:
            logger.debug(f"✅ 写入DB块的整数成功 - DB{db_number}@{start} = {value}")
            return True
        else:
            logger.error(f"❌ 写入DB块的整数失败")
            return False
        
    def wait_for_bit_change(
            self,
            db_number: int,
            byte_address: int,
            bit_address: int,
            target_value: int,
            timeout: float = settings.PLC_ACTION_TIMEOUT
            ) -> bool:
        """[同步] 等待PLC指定的位状态变化为目标值
        
        Args:
            db_number: DB块编号
            byte_address: 字节地址。如 22
            bit_address: 位地址(0-7)。如 0
            target_value: 目标值 
            timeout: 超时时间（秒）
        """
        start_time = time.time()
        
        while True:
            # 读取当前值
            current_value = self.read_bit(db_number, byte_address, bit_address)
            
            if current_value == target_value:
                logger.debug(f"✅ PLC动作完成: DB{db_number}@{byte_address}.{bit_address} = {current_value}")
                return True
                
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"❌ 超时错误: 等待PLC动作超时 ({timeout}s)")
                return False
                
            # 等待一段时间再次检查
            time.sleep(0.5)

###############################################################
# 在FastAPI中这样使用：
###############################################################

# from fastapi import FastAPI
# from .plc_connection_module import PLCConnectionBase

# app = FastAPI()
# plc = PLCConnectionBase("192.168.8.30")

# @app.on_event("startup")
# async def startup():
#     # 异步连接PLC
#     if not await plc.async_connect():
#         raise RuntimeError("PLC连接失败")

# @app.on_event("shutdown")
# async def shutdown():
#     # 异步断开PLC连接
#     await plc.async_disconnect()

# @app.post("/set-bit")
# async def set_bit(db: int, address: float, value: int):
#     """设置位值（同步操作）"""
#     # 在异步环境中安全调用同步方法
#     loop = asyncio.get_running_loop()
#     await loop.run_in_executor(None, plc.write_bit, db, address, value)
#     return {"status": "success"}

# @app.get("/monitor-status")
# async def monitor_status():
#     """启动状态监控"""
#     async def on_condition_met():
#         print("条件满足！执行操作")
    
#     await plc.start_monitoring(
#         MONITOR_DB=10,
#         MONITOR_OFFSET=5.0,
#         BITS=1,
#         TARGET_VALUE=1,
#         CALLBACK=on_condition_met
#     )
#     return {"status": "监控已启动"}