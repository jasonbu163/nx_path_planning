# devices/car_connection_module.py
import asyncio
from typing import Optional
import logging
logger = logging.getLogger(__name__)

# from app.utils.devices_logger import DevicesLogger


class ConnectionAsync():
    """异步穿梭车连接模块 (基于asyncio)，直接使用字节码通信。"""
    def __init__(self, HOST: str, PORT: int):
        """初始化穿梭车连接模块。

        Args:
            HOST: 服务器主机地址, 如 "192.168.8.30"
            PORT: 服务器端口, 如 2504
        """
        # super().__init__(self.__class__.__name__)
        self._host = HOST
        self._port = PORT
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        
    def is_connected(self) -> bool:
        """检查连接状态。"""
        return self._connected and self.writer is not None and not self.writer.is_closing()
    
    def _handle_connection_error(self, error: Exception):
        """统一处理连接错误。"""
        self._connected = False
        error_type = type(error).__name__
        logger.error(f"[CAR] 连接失败 {error_type}: {error}")
        if self.writer and not self.writer.is_closing():
            self.writer.close()

    async def connect(self, timeout: float = 5.0) -> bool:
        """[异步] 连接到TCP服务器。"""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=timeout
            )
            self._connected = True
            logger.info(f"[CAR] 已连接到服务器 {self._host}:{self._port}")
            return True
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
            self._handle_connection_error(e)
            return False
    
    
    async def send_message(self, message: str | bytes) -> bool:
        """发送消息到服务器。"""

        if not self.is_connected():
            logger.warning("[CAR] 发送失败：连接未建立")
            return False
        
        if self.writer is None:
            logger.warning("[CAR] 写入器未初始化")
            return False
        
        try:
            if isinstance(message, str):
                message = message.encode()
 
            self.writer.write(message)
            await self.writer.drain()
            logger.info(f"[CAR] 已发送: {message[:64]}{'...' if len(message)>64 else ''}")
            return True
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.error(f"[CAR] 发送失败: {e}")
            self._connected = False
            return False
    
    async def receive_message(self, timeout: float = 10.0) -> bytes:
    # async def receive_message(self, decode: bool = False, timeout: float = 10.0) -> Optional[bytes]:
        """接收服务器响应。

        - 后续如需要使用解码，请加入decode参数
        """
        if not self.is_connected():
            logger.warning("[CAR] 接收失败：连接未建立")
            return b'\x00'
        
        if self.reader is None:
            logger.warning("[CAR] 读取器未初始化")
            return b'\x00'

        try:
            data = await asyncio.wait_for(self.reader.read(1024), timeout=timeout)
            if not data:
                logger.warning("[CAR] 连接被远程关闭")
                self._connected = False
                return b'\x00'
            
            # 返回解码的数据 (使用请解除注释)
            # response = data.decode() if decode else data
            # logger.info(f"[CAR] 收到回复: {response[:128]}{'...' if len(response)>128 else ''}")
            # return response

            # 返回原始数据
            logger.debug(f"[CAR] 收到原始字节({len(data)}字节): {data[:8]}...")
            return data

        except (asyncio.TimeoutError, ConnectionResetError, OSError) as e:
            error_type = type(e).__name__
            logger.error(f"[CAR] 接收错误 {error_type}: {e}")
            self._connected = False
            return b'\x00'

    async def close(self) -> bool:
        """[异步] 安全关闭连接。"""
        if not self._connected or self.writer is None:
            return True
            
        try:
            # 双保险关闭逻辑
            if self.writer:
                if not self.writer.is_closing():
                    self.writer.close()
                    await self.writer.wait_closed()
                    
            logger.info("[CAR] 连接已关闭")
            return True
        except Exception as e:
            logger.error(f"[CAR] 关闭连接时出错: {e}")
            return False
        finally:
            self._connected = False
            self.reader = None
            self.writer = None