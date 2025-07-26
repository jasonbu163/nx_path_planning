from enum import Enum

class CarStatus(Enum):
    """
    [穿梭车点位地址枚举] - 根据报文交互文档整理
    """
    
    def __init__(self, value, description):
        """
        [自定义枚举初始化]

        ::: param :::
            value: 枚举的实际值（存储在self._value_）
            description: 枚举的描述信息（可扩展其他属性）
        """
        self._value_ = value # 必须保留的枚举值赋值
        self._description = description # 自定义属性
    
    @property
    def value(self):
        """
        [覆盖默认的value属性获取方式]
        """
        return self._value_
    
    @property
    def description(self):
        """
        [获取枚举的描述信息] - 符合WCS/WMS系统交互需求的描述信息
        """
        return self._description
    
    ######################
    ###### 穿梭车状态 #####
    #####################
    CAR_TASK_PROGRESS = 1, "任务执行中"
    CAR_CMD_PROGRESS = 2, "命令执行中"
    CAR_READY = 3, "就绪"
    CAR_PAUSE = 4, "暂停"
    CAR_POWER_CHARGE = 5, "充电中"
    CAR_ERROR = 6, "故障"
    CAR_SLEEP = 7, "休眠状态"
    CAR_STANDBY = 11, "节点待命"
    
if __name__ == "__main__":
    # 测试枚举类
    for car in CarStatus:
        print(f"{car.name}: {car.value} - {car.description}")