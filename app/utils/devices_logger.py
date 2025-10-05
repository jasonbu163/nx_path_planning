# devices/devices_logger.py
import logging
import os
from typing import Optional
from logging.handlers import RotatingFileHandler

class DevicesLogger:
    """设备日志记录器。用于设备的日志记录。"""
    def __init__(
            self,
            logger_name: str,
            log_file: Optional[str] = None,
            max_bytes:int = 10*1024*1024,
            backup_count: int = 5
    ) -> None:
        """初始化日志记录器。

        Args:
            logger_name: 日志记录器的名称, 保留了输入的参数，可以自定义日志记录名称
        """
        self._logger_name = logger_name
        self.logger = self.setup_logger(self._logger_name)
        
    def setup_logger(self, logger_name):
        """创建一个日志记录器

        Args:
            logger_name (str): [日志记录器的名称]

        Returns:
            logger (logging.Logger): [日志记录器对象]
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # 检查是否已经存在handler，避免重复添加导致日志重复输出
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s -  %(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger