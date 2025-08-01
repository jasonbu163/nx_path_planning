# devices/car_connection_module.py
import asyncio
from .devices_logger import DevicesLogger

class CarConnectionBase(DevicesLogger):
    """
    穿梭车连接模块
    """
    def __init__(self, HOST: str, PORT: int):
        """
        [初始化穿梭车连接模块]

        ::: param :::
            HOST: 服务器主机地址, 如 "192.168.8.30"
            PORT: 服务器端口, 如 2504
        """
        super().__init__(self.__class__.__name__)
        self._host = HOST
        self._port = PORT
        self.reader = None
        self.writer = None
        self._connected = False
        
    async def connect(self) -> bool:
        """
        [连接到TCP服务器]
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(self._host, self._port)
            self._connected = True
            self.logger.info(f"[CAR] 已连接到服务器 {self._host}:{self._port}")
        except ConnectionRefusedError:
            self._connected = False
            self.logger.error("[CAR] 无法连接到服务器")
        return self._connected
    
    async def send_message(self, message) -> bool:
        """
        [发送消息到服务器]\n
        ::: param :::\n
        message: 要发送的消息内容
        """
        if not self.writer:
            return False
        
        self.writer.write(message)
        await self.writer.drain()
        self.logger.info(f"[CAR] 已发送: {message}")
        return True
    
    async def receive_message(self):
        """
        [接收服务器响应]

        ::: return :::
            服务器返回的消息
        """
        if not self.reader:
            return None
        
        data = await self.reader.read(1024)
        if not data:
            return None
        
        # response = data.decode()
        response = data
        self.logger.info(f"[CAR] 收到服务端回复: {response}")
        return response
    
    async def close(self) -> bool:
        """
        [关闭连接]
        """
        if self._connected and self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self._connected = False
            self.logger.info("[CAR] 连接已关闭")
        return True
    
    