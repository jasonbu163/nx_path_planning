# app/core/connection.py
from abc import ABC, abstractmethod
from typing import Optional

class BaseConnection(ABC):
    """连接抽象基类。负责底层通信链路的生命周期管理。"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接到目标设备。返回连接是否成功。"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开与目标设备的连接。"""
        pass
    
    @abstractmethod
    def read(self, address: str, length: int) -> bytes:
        """从指定地址读取指定长度的原始字节数据。"""
        pass
    
    @abstractmethod
    def write(self, address: str, data: bytes) -> bool:
        """向指定地址写入原始字节数据。返回写入是否成功。"""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """获取当前连接状态。"""
        pass