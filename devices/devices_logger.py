# devices/devices_logger.py
import logging

class DevicesLogger:
    def __init__(self, LOGGER_NAME: str):
        self._logger_name = LOGGER_NAME
        self.logger = self.setup_logger(self._logger_name)
    def setup_logger(self, logger_name):
        """设置日志记录器"""
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s -  %(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger