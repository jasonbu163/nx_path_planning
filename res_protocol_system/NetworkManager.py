# res_protocol_system/NetworkManager.py
# -*- coding: utf-8 -*-
"""
RES+3.1 穿梭车通信协议上位机系统 - 模块化设计
按功能划分不同模块，便于团队协作维护
"""

import socket
import asyncio
from typing import Union

from devices.devices_logger import DevicesLogger

# ------------------------
# 模块 4: 通信处理器
# 职责: 管理网络连接和数据传输
# 维护者: 网络通信工程师
# ------------------------
class NetworkManager(DevicesLogger):
    """
    [网络处理器] - 这是一个用socket封装的异步网络处理器类
    """
    def __init__(self, HOST, PORT):
        super().__init__(self.__class__.__name__)
        self._host = HOST
        self._port = PORT
        self.sock = None
        self.reconnect_attempts = 0
        self.max_reconnect = 5
    
    async def connect(self) -> bool:
        """
        [建立TCP连接]
        """
        try:
            if self.sock:
                self.sock.close()
                
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 禁用Nagle算法
            self.sock.settimeout(3.0)  # 设置超时3秒
            self.logger.info(f"[网络] 正在连接到 {self._host}:{self._port}")  # 添加连接日志
            
            # 添加连接目标服务器的步骤
            server_address = (self._host, self._port)  # 需要替换为实际服务器地址
            await asyncio.get_event_loop().sock_connect(self.sock, server_address)
            
            self.reconnect_attempts = 0
            self.logger.info(f"[网络] 连接成功")
            # logger.info("[网络] 连接成功")  # 添加连接成功日志
            return True
        except socket.error as e:
            self.logger.error(f"连接失败: {str(e)} 错误码: {e.errno}")
            self.logger.info(f"检查服务器是否运行，防火墙是否开放端口")
            self.reconnect_attempts += 1
            # 添加自动重连机制
            if self.reconnect_attempts < 3:
                await asyncio.sleep(1)
                return await self.connect()
            return False
        except Exception as ex:
            self.logger.error(f"未知错误: {str(ex)}")
            return False

    async def send(self, PACKET: bytes) -> bool:
        """
        [发送数据包]

        ::: param :::
            PACKET: 要发送的数据包
        """
        try:
            if not self.sock:
                if not await self.connect():
                    return False
            
            # 使用asyncio的write方法发送数据
            assert self.sock is not None  # 添加类型断言消除Pylance错误
            self.sock.send(PACKET)
            return True
        except socket.error as e:
            self.logger.error(f"发送失败: {str(e)}")
            return False
    
    async def receive(
            self,
            TIMEOUT: float=1.0
            ) -> Union[bytes, None]:
        """
        [接收数据包]
        
        ::: param :::
            TIMEOUT: 接收超时时间，默认为1.0秒
        """
        if not self.sock:
            return None
            
        try:
            # 设置接收超时时间
            self.sock.settimeout(TIMEOUT)
            
            # 使用asyncio的read方法接收数据
            loop = asyncio.get_event_loop()
            data = await loop.sock_recv(self.sock, 2048)
            
            if not data:  # 空数据表示连接关闭
                self.logger.warning("检测到连接断开，空数据")
                await self.reconnect()
                return None
                
            self.logger.info(f"收到数据包: {data}")  # 打印收到的数据包
            return data
        except socket.timeout:
            # 超时属于正常情况，不视为错误
            self.logger.warning("接收超时，等待下一次数据")
            return None
        except socket.error as e:
            # 处理特定的socket错误
            if e.errno == 104:  # ECONNRESET
                self.logger.warning("检测到连接被对端重置")
            elif e.errno == 65:  # EHOSTUNREACH
                self.logger.warning("无法到达目标主机")
            else:
                self.logger.error(f"未知的socket错误: {e.errno}")
                
            await self.reconnect()
            return None
        except Exception as ex:
            self.logger.error(f"未知接收错误: {str(ex)}")
            return None

    async def reconnect(self) -> bool:
        """重新连接机制"""
        if self.sock:
            self.sock.close()
            self.sock = None
        
        if self.reconnect_attempts < self.max_reconnect:
            self.logger.info(f"尝试重连... (尝试次数: {self.reconnect_attempts + 1})")
            await asyncio.sleep(2)  # 等待2秒后重连
            if await self.connect():
                self.logger.info("重连成功")
                return True
        return False

    async def close(self) -> None:
        """关闭连接"""
        if self.sock:
            self.sock.close()
            self.sock = None