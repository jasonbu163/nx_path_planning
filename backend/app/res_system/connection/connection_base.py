# devices/car_connection_module.py
import socket
import time
from typing import Optional
import logging
logger = logging.getLogger(__name__)

# from app.utils.devices_logger import DevicesLogger


class ConnectionBase():
    """同步穿梭车连接模块 (基于原生Socket实现)。"""
    def __init__(self, HOST: str, PORT: int):
        # super().__init__(self.__class__.__name__)
        self._host = HOST
        self._port = PORT
        self._socket: Optional[socket.socket] = None
        self._connected = False
        
    def is_connected(self) -> bool:
        """检查连接状态。"""
        return self._connected and self._socket is not None
    
    def connect(self, retry_count: int = 5, retry_interval: float = 3.0) -> bool:
        """连接到TCP服务器(同步阻塞)。"""
        if self._connected:
            logger.warning("[CAR] 尝试连接但连接已存在，先关闭现有连接")
            self.close()
        
        for attempt in range(1, retry_count + 1):
            try:
                logger.info(f"[CAR] 连接尝试 {attempt}/{retry_count} {self._host}:{self._port}")
                
                # 创建新的socket实例
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # 设置超时和地址重用
                self._socket.settimeout(5.0)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # 禁用Nagle算法
                self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                # 尝试连接
                self._socket.connect((self._host, self._port))
                self._connected = True
                
                logger.info(f"[CAR] 连接成功 (尝试次数：{attempt})")
                return True
                
            except (socket.error, TimeoutError, OSError) as e:
                self._cleanup_socket()
                logger.error(f"[CAR] 连接失败 {attempt}/{retry_count}: {str(e)}")
                
                if attempt < retry_count:
                    logger.error(f"[CAR] 连接失败 {retry_interval} 秒后尝试重连...")
                    time.sleep(retry_interval)
                else:
                    logger.error(f"[CAR] 已达到最大重连次数（{retry_count}），连接终止")

        self._connected = False
        return False
    
    def send_message(self, message: bytes) -> bool:
    # def send_message(self, message: str | bytes) -> bool:
        """发送消息到服务器。"""
        if not self.is_connected() or self._socket is None:
            logger.error("[CAR] 发送失败：未建立有效连接")
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
                
            # logger.debug(f"[CAR] 已发送({len(message)}字节): {message[:32]}{'...' if len(message)>32 else ''}")
            logger.debug(f"[CAR] 已发送原始字节({len(message)}字节): {message[:8]}...")
            return True
            
        except (socket.error, OSError) as e:
            logger.error(f"[CAR] 发送失败: {str(e)}")
            self.close()
            return False
    
    def receive_message(self, timeout: float = 10.0, max_bytes: int = 4096) -> bytes:
        """接收服务器响应。"""
        if not self.is_connected() or self._socket is None:
            logger.error("[CAR] 接收失败：未建立有效连接")
            return b'\x00'
            
        try:
            self._socket.settimeout(timeout)
            data = self._socket.recv(max_bytes)
            
            if not data:
                logger.warning("[CAR] 连接已由服务端关闭")
                self.close()
                return b'\x00'
                
            # 注意：当前项目直接返回原始字节数据
            # 如果未来需要字符串，可取消以下注释：
            # logger.info(f"[CAR] 收到({len(data)}字节): {data[:128]}{'...' if len(data)>128 else ''}")
            logger.debug(f"[CAR] 收到原始字节({len(data)}字节): {data[:8]}...")
            return data
            
        except socket.timeout:
            logger.warning("[CAR] 接收超时，未接收到数据")
            return b'\x00'
        except (socket.error, OSError) as e:
            logger.error(f"[CAR] 接收错误: {str(e)}")
            self.close()
            return b'\x00'
    
    def close(self) -> bool:
        """安全关闭连接并清理资源。"""
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
                logger.info("[CAR] 连接已关闭")
                
        except Exception as e:
            logger.error(f"[CAR] 关闭连接时出错: {str(e)}")
            return False
            
        finally:
            self._cleanup_socket()
            
        return True
    
    def _cleanup_socket(self):
        """彻底清理socket资源。"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass  # 忽略关闭时可能出现的错误
        self._socket = None
        self._connected = False