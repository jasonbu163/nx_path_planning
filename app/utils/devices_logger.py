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
            max_bytes: int = 10*1024*1024,
            backup_count: int = 5
    ) -> None:
        """初始化日志记录器。

        Args:
            logger_name: 日志记录器的名称, 保留了输入的参数，可以自定义日志记录名称。
            log_file: 日志文件的路劲。默认为None，表示使用默认日志文件名。
            max_bytes: 当个日志文件的最大字节数。默认值为10MB。
            backup_count: 保留的日志文件数量。默认值为5个。
        """
        self._name = logger_name
        self._log_file = log_file or f'app/logs/{logger_name}.log'
        self._max_bytes = max_bytes
        self._backup_count = backup_count

        # 日志记录器
        self.logger = self.setup_logger()
        
    def setup_logger(self):
        """创建一个日志记录器

        Args:
            logger_name (str): [日志记录器的名称]

        Returns:
            logger (logging.Logger): [日志记录器对象]
        """
        logger = logging.getLogger(self._name)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s -  %(levelname)s] %(message)s')
        
        # 检查是否已经存在handler，避免重复添加导致日志重复输出
        if not logger.handlers:
            log_dir = os.path.dirname(self._log_file)
            if log_dir and not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                except OSError:
                    # 如果无法创建目录，则使用默认日志文件名
                    self._log_file = os.path.basename(self._log_file)
            
            # 创建一个轮转文件handler，指定UTF-8编码
            try:
                fh = RotatingFileHandler(
                    self._log_file,
                    maxBytes=self._max_bytes,
                    backupCount=self._backup_count,
                    encoding='utf-8'
                )
                fh.setLevel(logging.INFO)
                fh.setFormatter(formatter)
                logger.addHandler(fh)
            except IOError:
                # 如果无法创建文件，则只输出到控制台
                pass

            sh = logging.StreamHandler()
            sh.setLevel(logging.INFO)
            sh.setFormatter(formatter)
            logger.addHandler(sh)

        return logger
    
    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)