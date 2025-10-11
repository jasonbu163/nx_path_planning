# tests/test_db.py
from sys_path import setup_path
setup_path()

import time

from enum import Enum

from app.plc_system.enum import PLCAddressBase
from app.res_system.enum import CarStatus, StatusDescription

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

def test_3():
    
    # 测试枚举类
    # for status in WorkCommand:
    #     print(f"{status.name}: {status.value} - {status.description}")
    
    # print(ImmediateCommand.CANCEL_TASK.value)

    # 假设状态码来自某个响应报文
    received_status_code = 1

    result = CarStatus.get_by_value(received_status_code)
    print(result)

    name = CarStatus.get_info_by_value(received_status_code).get('name')
    des = CarStatus.get_info_by_value(received_status_code).get('description')
    print(f"{name}: {received_status_code} - {des}")

    # name = StatusDescription.get_info_by_value(received_warning_code).get('name')
    # des = StatusDescription.get_info_by_value(received_warning_code).get('description')
    # print(f"{name}: {received_warning_code} - {des}")

def main():
    """同步测试"""

    start = time.time()

    # test_1()
    # test_2()
    test_3()

    elapsed = time.time() - start
    print(f"程序用时: {elapsed:.6f}s")
    

if __name__ == "__main__":
    main()
