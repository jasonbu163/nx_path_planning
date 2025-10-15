# app/core/client.py

from abc import ABC, abstractmethod
from typing import Any
from .connection import BaseConnection  # 引入上面的连接基类

class BasePLCClient(ABC):
    """PLC客户端抽象基类。提供高级的、面向业务的数据读写操作。"""
    
    def __init__(self, connection: BaseConnection):
        # 依赖注入：客户端并不关心连接的具体协议和实现方式（同步/异步），
        # 它只依赖于BaseConnection这个抽象接口。
        self._connection = connection
    
    @abstractmethod
    def read_tag(self, tag: str, data_type: type) -> Any:
        """
        读取一个PLC标签的值。
        例如: read_tag("DB10.DBD4", float)
        """
        pass
    
    @abstractmethod
    def write_tag(self, tag: str, value: Any) -> bool:
        """
        向一个PLC标签写入值。
        例如: write_tag("MW20", 100)
        """
        pass
    
    def connect(self) -> bool:
        """委托给内部的连接对象进行连接。"""
        return self._connection.connect()
    
    def disconnect(self) -> None:
        """委托给内部的连接对象断开连接。"""
        self._connection.disconnect()
    
    @property
    def is_connected(self) -> bool:
        """获取当前连接状态。"""
        return self._connection.is_connected