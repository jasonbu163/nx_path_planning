import asyncio
import socket
import time
import random
from typing import Optional, Callable
from enum import Enum
import logging

from app.utils.devices_logger import DevicesLogger

class ConnectionStatus(Enum):
    """连接状态机"""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 3
    RECONNECTING = 4

class IndustrialConnectionBase(DevicesLogger):
    """工业通信基类（同步版优化）
    
    优化重点：连接可靠性、资源管理、可观测性。
    """
    def __init__(self, host: str, port: int):
        super().__init__(self.__class__.__name__)
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._status = ConnectionStatus.DISCONNECTED
        
        # === 工业级可配置参数 ===
        self._timeout = 10.0
        self._max_retries = 5
        self._base_reconnect_delay = 1.0  # 指数退避基值
        self._heartbeat_interval = 30
        self._last_heartbeat_sent = 0
        
        # 回调函数
        self._on_connection_change: Optional[Callable] = None
        
    def _update_status(self, new_status: ConnectionStatus):
        """统一更新状态并触发回调"""
        if self._status != new_status:
            old_status = self._status
            self._status = new_status
            self.logger.info(f"[NET] 连接状态变更: {old_status.name} -> {new_status.name}")
            if self._on_connection_change:
                self._on_connection_change(old_status, new_status)

    def _exponential_backoff(self, attempt: int) -> float:
        """指数退避算法，避免重连风暴[1](@ref)"""
        delay = self._base_reconnect_delay * (2 ** attempt)
        jitter = random.uniform(0, delay * 0.1)  # 加入随机抖动，避免多个客户端同时重连
        return min(delay + jitter, 30)  # 设置最大延迟

    def connect(self, retry_count: int = None) -> bool:
        """工业级连接建立（同步阻塞）"""
        if self._status in (ConnectionStatus.CONNECTED, ConnectionStatus.CONNECTING):
            self.logger.warning("[NET] 连接已存在或正在建立中")
            return True

        self._update_status(ConnectionStatus.CONNECTING)
        max_attempts = retry_count if retry_count is not None else self._max_retries

        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.info(f"[NET] 连接尝试 {attempt}/{max_attempts} to {self._host}:{self._port}")
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(self._timeout)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 禁用Nagle算法
                
                self._socket.connect((self._host, self._port))
                self._update_status(ConnectionStatus.CONNECTED)
                self._last_heartbeat_sent = time.time()
                self.logger.info(f"[NET] 连接成功建立 (尝试次数: {attempt})")
                return True
                
            except (socket.timeout, ConnectionRefusedError, OSError) as e:
                self.logger.error(f"[NET] 连接失败 {attempt}/{max_attempts}: {e}")
                self._cleanup_socket()
                
                if attempt < max_attempts:
                    delay = self._exponential_backoff(attempt)
                    self.logger.info(f"[NET] {delay:.2f}秒后尝试重连...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"[NET] 已达到最大重试次数({max_attempts})，连接终止")
                    self._update_status(ConnectionStatus.ERROR)
        
        return False

    def send_message(self, message: bytes) -> bool:
        """发送数据（确保完整发送）"""
        if not self.is_connected():
            self.logger.error("[NET] 发送失败：连接未就绪")
            return False

        try:
            total_sent = 0
            while total_sent < len(message):
                sent = self._socket.send(message[total_sent:])
                if sent == 0:
                    raise ConnectionError("Socket连接已断开")
                total_sent += sent
                
            self.logger.debug(f"[NET] 数据发送成功, 长度: {len(message)} 字节")
            self._last_heartbeat_sent = time.time()  # 重置心跳计时
            return True
            
        except (socket.error, OSError, ConnectionError) as e:
            self.logger.error(f"[NET] 数据发送失败: {e}")
            self._handle_connection_error()
            return False

    def receive_message(self, timeout: float = 10.0, max_bytes: int = 4096) -> bytes:
        """接收数据（带超时控制）"""
        if not self.is_connected():
            self.logger.error("[NET] 接收失败：连接未就绪")
            return b''

        try:
            self._socket.settimeout(timeout)
            data = self._socket.recv(max_bytes)
            if not data:
                self.logger.warning("[NET] 对端关闭了连接")
                self._handle_connection_error()
                return b''
                
            self.logger.debug(f"[NET] 数据接收成功, 长度: {len(data)} 字节")
            return data
            
        except socket.timeout:
            self.logger.warning(f"[NET] 接收超时 ({timeout}秒)")
            return b''
        except (socket.error, OSError) as e:
            self.logger.error(f"[NET] 接收错误: {e}")
            self._handle_connection_error()
            return b''

    def _handle_connection_error(self):
        """统一的连接错误处理"""
        self._cleanup_socket()
        self._update_status(ConnectionStatus.ERROR)

    def _cleanup_socket(self):
        """安全的资源清理"""
        if self._socket:
            try:
                self._socket.close()
            except Exception as e:
                self.logger.debug(f"[NET] 关闭socket时忽略异常: {e}")
            finally:
                self._socket = None

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._status == ConnectionStatus.CONNECTED and self._socket is not None

    def close(self):
        """安全关闭连接"""
        if self._status == ConnectionStatus.DISCONNECTED:
            return
            
        self.logger.info("[NET] 正在安全关闭连接...")
        self._cleanup_socket()
        self._update_status(ConnectionStatus.DISCONNECTED)

    def set_connection_callback(self, callback: Callable):
        """设置连接状态变化回调"""
        self._on_connection_change = callback

    # 支持上下文管理器
    def __enter__(self):
        if self.connect():
            return self
        raise ConnectionError(f"无法连接到 {self._host}:{self._port}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class IndustrialAsyncConnection(DevicesLogger):
    """工业通信基类（异步版优化）
    
    优化重点：异步并发控制、心跳保活、优雅关闭。
    """
    def __init__(self, host: str, port: int):
        super().__init__(self.__class__.__name__)
        self._host = host
        self._port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._status = ConnectionStatus.DISCONNECTED
        
        # === 工业级可配置参数 ===
        self._timeout = 10.0
        self._max_retries = 5
        self._base_reconnect_delay = 1.0
        self._heartbeat_interval = 30
        
        # 异步任务管理
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
    def _update_status(self, new_status: ConnectionStatus):
        """统一更新状态"""
        if self._status != new_status:
            old_status = self._status
            self._status = new_status
            self.logger.info(f"[NET] 连接状态变更: {old_status.name} -> {new_status.name}")

    async def connect(self, timeout: float = None) -> bool:
        """工业级连接建立（异步非阻塞）"""
        async with self._lock:  # 防止并发连接
            if self._status in (ConnectionStatus.CONNECTED, ConnectionStatus.CONNECTING):
                self.logger.warning("[NET] 连接已存在或正在建立中")
                return True

            self._update_status(ConnectionStatus.CONNECTING)
            connect_timeout = timeout or self._timeout

            for attempt in range(1, self._max_retries + 1):
                try:
                    self.logger.info(f"[NET] 异步连接尝试 {attempt}/{self._max_retries}")
                    self._reader, self._writer = await asyncio.wait_for(
                        asyncio.open_connection(self._host, self._port),
                        timeout=connect_timeout
                    )
                    self._update_status(ConnectionStatus.CONNECTED)
                    self._start_background_tasks()
                    self.logger.info(f"[NET] 异步连接成功建立 (尝试次数: {attempt})")
                    return True
                    
                except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                    self.logger.error(f"[NET] 异步连接失败 {attempt}/{self._max_retries}: {e}")
                    await self._cleanup_streams()
                    
                    if attempt < self._max_retries:
                        delay = self._exponential_backoff(attempt)
                        self.logger.info(f"[NET] {delay:.2f}秒后尝试异步重连...")
                        await asyncio.sleep(delay)
                    else:
                        self.logger.error(f"[NET] 已达到最大重试次数，异步连接终止")
                        self._update_status(ConnectionStatus.ERROR)
            
            return False

    async def send_message(self, message: bytes) -> bool:
        """异步发送数据"""
        if not self.is_connected() or self._writer is None:
            self.logger.error("[NET] 异步发送失败：连接未就绪")
            return False

        try:
            self._writer.write(message)
            await asyncio.wait_for(self._writer.drain(), timeout=self._timeout)
            self.logger.debug(f"[NET] 异步数据发送成功, 长度: {len(message)} 字节")
            return True
            
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"[NET] 异步数据发送失败: {e}")
            await self._handle_connection_error()
            return False

    async def receive_message(self, timeout: float = 10.0) -> bytes:
        """异步接收数据"""
        if not self.is_connected() or self._reader is None:
            self.logger.error("[NET] 异步接收失败：连接未就绪")
            return b''

        try:
            data = await asyncio.wait_for(self._reader.read(1024), timeout=timeout)
            if not data:
                self.logger.warning("[NET] 对端关闭了异步连接")
                await self._handle_connection_error()
                return b''
                
            self.logger.debug(f"[NET] 异步数据接收成功, 长度: {len(data)} 字节")
            return data
            
        except asyncio.TimeoutError:
            self.logger.warning(f"[NET] 异步接收超时 ({timeout}秒)")
            return b''
        except (ConnectionError, OSError) as e:
            self.logger.error(f"[NET] 异步接收错误: {e}")
            await self._handle_connection_error()
            return b''

    def _start_background_tasks(self):
        """启动后台维护任务（如心跳）"""
        # 可根据需要在此处添加心跳任务
        # self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        pass

    async def _heartbeat_loop(self):
        """心跳保活循环（示例）"""
        while self.is_connected() and self._writer:
            try:
                # 发送心跳包的逻辑由协议模块决定，这里只是框架
                await asyncio.sleep(self._heartbeat_interval)
                if time.time() - self._last_heartbeat_sent > self._heartbeat_interval:
                    self.logger.debug("[NET] 发送心跳包")
                    # 实际心跳包发送应由协议模块调用send_message实现
                    self._last_heartbeat_sent = time.time()
            except Exception as e:
                self.logger.error(f"[NET] 心跳任务异常: {e}")
                break

    async def _handle_connection_error(self):
        """异步连接错误处理"""
        await self._cleanup_streams()
        self._update_status(ConnectionStatus.ERROR)

    async def _cleanup_streams(self):
        """安全的异步资源清理"""
        if self._writer:
            try:
                self._writer.close()
                await asyncio.wait_for(self._writer.wait_closed(), timeout=2.0)
            except Exception as e:
                self.logger.debug(f"[NET] 关闭writer时忽略异常: {e}")
            finally:
                self._reader, self._writer = None, None

        # 取消后台任务
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

    def is_connected(self) -> bool:
        """检查异步连接状态"""
        return (self._status == ConnectionStatus.CONNECTED and 
                self._writer is not None and 
                not self._writer.is_closing())

    async def close(self):
        """安全关闭异步连接"""
        if self._status == ConnectionStatus.DISCONNECTED:
            return
            
        self.logger.info("[NET] 正在安全关闭异步连接...")
        await self._cleanup_streams()
        self._update_status(ConnectionStatus.DISCONNECTED)

    # 异步上下文管理器
    async def __aenter__(self):
        if await self.connect():
            return self
        raise ConnectionError(f"无法异步连接到 {self._host}:{self._port}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()