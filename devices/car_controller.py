# devices/car_controller.py

from typing import Any
from .car_connection_module import CarConnectionBase
from .car_enum import CarStatus

class CarController(CarConnectionBase):
    """
    [穿梭车 - 高级操作类]
    """

    def __init__(self, CAR_IP: str, CAR_PORT: int):
        """
        [初始化穿梭车客户端]

        ::: param :::
            CAR_IP: plc地址, 如 “192.168.3.30”
            CAR_PORT: plc端口, 如 2504
        """
        super().__init__(CAR_IP, CAR_PORT)