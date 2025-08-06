# devices/car_connection_module.py
import asyncio
import socket
import time
from typing import Optional, Union

from .devices_logger import DevicesLogger

class CarConnection(DevicesLogger):
    """
    [穿梭车连接模块] 异步穿梭车连接模块 (基于asyncio)，直接使用字节码通信
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
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        
    def is_connected(self) -> bool:
        """
        [检查连接状态]
        """
        return self._connected and self.writer is not None and not self.writer.is_closing()
    
    def _handle_connection_error(self, error: Exception):
        """
        [统一处理连接错误]
        """
        self._connected = False
        error_type = type(error).__name__
        self.logger.error(f"[CAR] 连接失败 {error_type}: {error}")
        if self.writer and not self.writer.is_closing():
            self.writer.close()

    async def connect(self, timeout: float = 5.0) -> bool:
        """
        [异步连接器] 连接到TCP服务器
        """
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=timeout
            )
            self._connected = True
            self.logger.info(f"[CAR] 已连接到服务器 {self._host}:{self._port}")
            return True
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
            self._handle_connection_error(e)
            return False
    
    
    async def send_message(self, message: str | bytes) -> bool:
        """
        [数据发送器] 发送消息到服务器
        """
        if not self.is_connected():
            self.logger.warning("[CAR] 发送失败：连接未建立")
            return False
        
        if self.writer is None:
            self.logger.warning("[CAR] 写入器未初始化")
            return False
        
        try:
            if isinstance(message, str):
                message = message.encode()
 
            self.writer.write(message)
            await self.writer.drain()
            self.logger.info(f"[CAR] 已发送: {message[:64]}{'...' if len(message)>64 else ''}")
            return True
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            self.logger.error(f"[CAR] 发送失败: {e}")
            self._connected = False
            return False
    
    async def receive_message(self, timeout: float = 10.0) -> Optional[bytes]:
    # async def receive_message(self, decode: bool = False, timeout: float = 10.0) -> Optional[bytes]:
        """
        [数据接收器] 接收服务器响应
            后续如需要使用解码，请加入decode参数
        """
        if not self.is_connected():
            self.logger.warning("[CAR] 接收失败：连接未建立")
            return None
        
        if self.reader is None:
            self.logger.warning("[CAR] 读取器未初始化")
            return None

        try:
            data = await asyncio.wait_for(self.reader.read(1024), timeout=timeout)
            if not data:
                self.logger.warning("[CAR] 连接被远程关闭")
                self._connected = False
                return None
            
            # 返回解码的数据 (使用请解除注释)
            # response = data.decode() if decode else data
            # self.logger.info(f"[CAR] 收到回复: {response[:128]}{'...' if len(response)>128 else ''}")
            # return response

            # 返回原始数据
            self.logger.info(f"[CAR] 收到原始字节({len(data)}字节): {data[:8]}...")
            return data

        except (asyncio.TimeoutError, ConnectionResetError, OSError) as e:
            error_type = type(e).__name__
            self.logger.error(f"[CAR] 接收错误 {error_type}: {e}")
            self._connected = False
            return None

    async def close(self) -> bool:
        """
        [异步关闭连接] 安全关闭连接
        """
        if not self._connected or self.writer is None:
            return True
            
        try:
            # 双保险关闭逻辑
            if self.writer:
                if not self.writer.is_closing():
                    self.writer.close()
                    await self.writer.wait_closed()
                    
            self.logger.info("[CAR] 连接已关闭")
            return True
        except Exception as e:
            self.logger.error(f"[CAR] 关闭连接时出错: {e}")
            return False
        finally:
            self._connected = False
            self.reader = None
            self.writer = None
    

class CarConnectionBase(DevicesLogger):
    """
    [穿梭车连接模块] 同步穿梭车连接模块 (基于原生Socket实现)
    """
    def __init__(self, HOST: str, PORT: int):
        super().__init__(self.__class__.__name__)
        self._host = HOST
        self._port = PORT
        self._socket: Optional[socket.socket] = None
        self._connected = False
        
    def is_connected(self) -> bool:
        """
        [检查连接状态]
        """
        return self._connected and self._socket is not None
    
    def connect(self, retry_count: int = 3, retry_interval: float = 2.0) -> bool:
        """
        [同步连接器] 连接到TCP服务器 (同步阻塞版本)
        """
        if self._connected:
            self.logger.warning("[CAR] 尝试连接但连接已存在，先关闭现有连接")
            self.close()
        
        for attempt in range(1, retry_count + 1):
            try:
                self.logger.info(f"[CAR] 连接尝试 {attempt}/{retry_count} {self._host}:{self._port}")
                
                # 创建新的socket实例
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                # 设置超时和地址重用
                self._socket.settimeout(5.0)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # 尝试连接
                self._socket.connect((self._host, self._port))
                self._connected = True
                
                # 禁用Nagle算法
                self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                self.logger.info(f"[CAR] 连接成功 {self._host}:{self._port}")
                return True
                
            except (socket.error, TimeoutError, OSError) as e:
                self._cleanup_socket()
                self.logger.error(f"[CAR] 连接失败 {attempt}/{retry_count}: {str(e)}")
                
                if attempt < retry_count:
                    time.sleep(retry_interval)
        
        self._connected = False
        return False
    
    def send_message(self, message: bytes) -> bool:
    # def send_message(self, message: str | bytes) -> bool:
        """
        [数据发送器] 发送消息到服务器
        """
        if not self.is_connected() or self._socket is None:
            self.logger.error("[CAR] 发送失败：未建立有效连接")
            return False
            
        try:
            # 注意：当前项目直接使用字节码通信
            # 如果未来需要支持字符串，可取消以下注释：
            # if isinstance(message, str):
            #     message = message.encode('utf-8')
                
            # 确保发送完整消息
            total_sent = 0
            while total_sent < len(message):
                sent = self._socket.send(message[total_sent:])
                if sent == 0:
                    raise RuntimeError("Socket连接中断")
                total_sent += sent
                
            # self.logger.info(f"[CAR] 已发送({len(message)}字节): {message[:32]}{'...' if len(message)>32 else ''}")
            self.logger.info(f"[CAR] 已发送原始字节({len(message)}字节): {message[:8]}...")
            return True
            
        except (socket.error, OSError) as e:
            self.logger.error(f"[CAR] 发送失败: {str(e)}")
            self.close()
            return False
    
    def receive_message(self, timeout: float = 10.0, max_bytes: int = 4096) -> Optional[bytes]:
        """
        [数据接收器] 接收服务器响应
        """
        if not self.is_connected() or self._socket is None:
            self.logger.error("[CAR] 接收失败：未建立有效连接")
            return None
            
        try:
            self._socket.settimeout(timeout)
            data = self._socket.recv(max_bytes)
            
            if not data:
                self.logger.warning("[CAR] 连接已由服务端关闭")
                self.close()
                return None
                
            # 注意：当前项目直接返回原始字节数据
            # 如果未来需要字符串，可取消以下注释：
            # self.logger.info(f"[CAR] 收到({len(data)}字节): {data[:128]}{'...' if len(data)>128 else ''}")
            self.logger.info(f"[CAR] 收到原始字节({len(data)}字节): {data[:8]}...")
            return data
            
        except socket.timeout:
            self.logger.warning("[CAR] 接收超时，未接收到数据")
            return None
        except (socket.error, OSError) as e:
            self.logger.error(f"[CAR] 接收错误: {str(e)}")
            self.close()
            return None
    
    def close(self) -> bool:
        """
        [关闭连接] 安全关闭连接并清理资源
        """
        if not self._connected:
            return True
            
        try:
            # 首先尝试优雅关闭
            if self._socket:
                try:
                    # 发送关闭通知（如果协议支持）
                    self._socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass  # 可能已经关闭
                
                # 实际关闭套接字
                self._socket.close()
                self.logger.info("[CAR] 连接已关闭")
                
        except Exception as e:
            self.logger.error(f"[CAR] 关闭连接时出错: {str(e)}")
            return False
            
        finally:
            self._cleanup_socket()
            
        return True
    
    def _cleanup_socket(self):
        """
        [彻底清理socket资源]
        """
        if self._socket:
            try:
                self._socket.close()
            except:
                pass  # 忽略关闭时可能出现的错误
        self._socket = None
        self._connected = False