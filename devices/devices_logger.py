# devices/devices_logger.py
import logging

class DevicesLogger:
    """
    [设备日志记录器] - 用于设备的日志记录
    """
    def __init__(self, LOGGER_NAME: str):
        """
        [初始化日志记录器]

        ::: param :::
            LOGGER_NAME: 日志记录器的名称, 保留了输入的参数，可以自定义日志记录名称
        """
        self._logger_name = LOGGER_NAME
        self.logger = self.setup_logger(self._logger_name)
    def setup_logger(self, logger_name):
        """
        [设置日志记录器] - 创建一个日志记录器

        ::: param :::
            logger_name (str): [日志记录器的名称]

        ::: return :::
            logger (logging.Logger): [日志记录器对象]
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s -  %(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger