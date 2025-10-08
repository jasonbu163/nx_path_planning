# tests/test_db.py
from sys_path import setup_path
setup_path()

import time

from enum import Enum

from app.plc_system.enum import PLCAddressBase

class DB_10(PLCAddressBase, Enum):

    def __init__(self, address, description):
        # 这里可以添加额外的初始化代码，例如验证地址格式
        self._value_: dict = address
        self._description: str = description # 自定义属性
    
    @property
    def value(self):
        """
        [显式操作] - 覆盖默认的value属性获取方式
        """
        return self._value_
    
    @property
    def description(self):
        """
        [获取枚举的描述信息] - 符合WCS/WMS系统交互需求的描述信息
        """
        return self._description
    
    FREQ_CONVERTER_ALARM = {"byte_address": 10, "bit_address": 0}, "变频报警"
    RUN_TIMEOUT = {"byte_address": 10, "bit_address": 1}, "运行超时"
    FRONT_CAR_OVERLIMIT = {"byte_address": 10, "bit_address": 2}, "前车超限"

class DB_12:
    
    FREQ_CONVERTER_ALARM = {"byte_address": 10, "bit_address": 0, "description": "变频报警"}
    RUN_TIMEOUT = {"byte_address": 10, "bit_address": 1, "description": "运行超时"}
    FRONT_CAR_OVERLIMIT = {"byte_address": 10, "bit_address": 2, "description": "前车超限"}
def test_1():

    print(DB_10.FREQ_CONVERTER_ALARM.value.get("bit_address"))

def test_2():

    print(DB_12.FREQ_CONVERTER_ALARM.get("bit_address"))

def main():
    """同步测试"""

    start = time.time()

    test_1()
    test_2()

    elapsed = time.time() - start
    print(f"程序用时: {elapsed:.6f}s")
    

if __name__ == "__main__":
    main()
