from enum import Enum
from typing import Union

class PLCAddressBase:
    """
    [PLC点位地址基类] - 仅作为类型标注和共享方法使用
    """
    @property
    def value(self) -> Union[int, float, str]:
        # 将在子类中实现
        raise NotImplementedError
    
    def is_float_address(self) -> bool:
        """
        [判断是否为浮点地址] - 带小数点的地址
        """
        value = self.value
        return isinstance(value, float) or (isinstance(value, str) and '.' in value)

class DB_12(PLCAddressBase, Enum):
    """
    [DB 12] - PLC点位地址枚举, 根据EXCEL点位表生成
    """
    def __init__(self, address, description):
        # 这里可以添加额外的初始化代码，例如验证地址格式
        self._value_ = address
        self._description = description # 自定义属性
    
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
    

    TASK_TYPE = 0, "任务类型: 1载货 2载车 3载货和车 4空载"
    START_LAYER = 2, "起始层"
    TARGET_LAYER = 4, "目标层"
    TASK_NUMBER = 6, "任务号"
    DISABLED = 8, "禁用"
    
    TARGET_1010 = 10, "1010目标"
    TARGET_1020 = 12, "1020目标"
    TARGET_1030 = 14, "1030目标"
    TARGET_1040 = 16, "1040目标"
    TARGET_1050 = 18, "1050目标"
    TARGET_1060 = 20, "1060目标"
    
    FEED_COMPLETE_1010 = 22.0, "1010放料完成"
    
    FEED_COMPLETE_1030 = 22.1, "1030放料完成"
    FEED_COMPLETE_1040 = 22.2, "1040放料完成"
    FEED_COMPLETE_1050 = 22.3, "1050放料完成"
    FEED_COMPLETE_1060 = 22.4, "1060放料完成"
    
    PICK_COMPLETE_1030 = 22.5, "1030取料完成"
    PICK_COMPLETE_1040 = 22.6, "1040取料完成"
    PICK_COMPLETE_1050 = 22.7, "1050取料完成"
    PICK_COMPLETE_1060 = 23.0, "1060取料完成"
    
    FEED_IN_PROGRESS_1030 = 23.1, "1030放料进行中"
    FEED_IN_PROGRESS_1040 = 23.2, "1040放料进行中"
    FEED_IN_PROGRESS_1050 = 23.3, "1050放料进行中"
    FEED_IN_PROGRESS_1060 = 23.4, "1060放料进行中"
    
    PICK_IN_PROGRESS_1030 = 23.5, "1030取料进行中"
    PICK_IN_PROGRESS_1040 = 23.6, "1040取料进行中"
    PICK_IN_PROGRESS_1050 = 23.7, "1050取料进行中"
    PICK_IN_PROGRESS_1060 = 24.0, "1060取料进行中"
    
    TARGET_LAYER_ARRIVED = 24.1, "目标层到达"
    

class DB_11(PLCAddressBase, Enum):
    """
    [DB 11] - PLC点位地址枚举, 根据EXCEL点位表生成
    """
    def __init__(self, address, description):
        # 这里可以添加额外的初始化代码，例如验证地址格式
        self._value_ = address
        self._description = description # 自定义属性
    
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
    

    FREQ_CONVERTER_ALARM = 10.0, "变频报警"
    RUN_TIMEOUT = 10.1, "运行超时"
    FRONT_CAR_OVERLIMIT = 10.2, "前车超限"
    REAR_CAR_OVERLIMIT = 10.3, "后车超限"
    FRONT_CARGO_OVERLIMIT = 10.4, "前货物超限"
    REAR_CARGO_OVERLIMIT = 10.5, "后货物超限"
    UPPER_LIMIT = 10.6, "上极限"
    LOWER_LIMIT = 10.7, "下极限"
    STALL = 11.0, "失速"
    BLOCKED_ROTATION = 11.1, "堵转"
    POSITION_ABNORMAL = 11.2, "位置异常"
    TARGET_COORD_ABNORMAL = 11.3, "给定坐标异常"
    BY = 11.4, "BY"
    BY_1 = 11.5, "BY_1"
    BY_2 = 11.6, "BY_2"
    BY_3 = 11.7, "BY_3"
    BY_4 = 12, "BY_4"
    MANUAL_MODE = 13.0, "手动"
    AUTO_MODE = 13.1, "自动"
    RUNNING = 13.2, "运行"
    IDLE = 13.3, "空闲"
    NO_CARGO = 13.4, "无货"
    HAS_CARGO = 13.5, "有货"
    HAS_CAR = 13.6, "有车"
    FAULT = 13.7, "故障"
    CURRENT_LAYER = 14, "提升机当前层"
    CURRENT_RWH = 16, "提升机当前RWH"
    CURRENT_MBH = 18, "提升机当前MBH"
    COMPLETED_RWH = 20, "提升机完成RWH"
    
    # 条码区域
    SCAN_CODE_RD = 22, "扫描二维码"
    
    # 重量和外形检测区域
    WEIGHT = 44, "Weight"
    WX_DATA = 46, "外形数据"
    ERROR_H = 48.0, "高度错误"
    ERROR_F = 48.1, "前部错误"
    ERROR_B = 48.2, "后部错误"
    ERROR_L = 48.3, "左侧错误"
    ERROR_R = 48.4, "右侧错误"
    ERROR_1 = 48.5, "错误1"
    ERROR_2 = 48.6, "错误2"
    ERROR_3 = 48.7, "错误3"
    H_DATA = 50, "高度数据"
    
    # 状态
    # 1: 无货, 没动
    # 0: 有货, 没动
    # 0: 无货, 移动中
    # 0: 有货, 移动中
    STATUS_1010 = 52.0, "1010状态"
    STATUS_1020 = 52.1, "1020状态"
    STATUS_1030 = 52.2, "1030状态"
    STATUS_1040 = 52.3, "1040状态"
    STATUS_1050 = 52.4, "1050状态"
    STATUS_1060 = 52.5, "1060状态"
    
    INBAND_START = 52.7, "入库放料完成"

    PLATFORM_PALLET_READY_MAN = 53.0, "1010载物台托盘到位(1到位0无), 出入口"
    PLATFORM_PALLET_READY_1020 = 52.6, "1020载物台托盘到位(1到位0无),电梯"
    PLATFORM_PALLET_READY_1030 = 53.1, "1030载物台托盘到位(1到位0无), 库内1层"
    PLATFORM_PALLET_READY_1040 = 53.2, "1040载物台托盘到位(1到位0无), 库内2层"
    PLATFORM_PALLET_READY_1050 = 53.3, "1050载物台托盘到位(1到位0无), 库内3层"
    PLATFORM_PALLET_READY_1060 = 53.4, "1060载物台托盘到位(1到位0无), 库内4层"


class DB_5(PLCAddressBase, Enum):
    """
    [DB 5] - PLC点位地址枚举, 根据EXCEL点位表生成
    """
    def __init__(self, address, description):
        # 这里可以添加额外的初始化代码，例如验证地址格式
        self._value_ = address
        self._description = description # 自定义属性
    
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
    
    ################
    ###### DB5 #####
    ################
    LIFT_UP = 0.0, "电梯上升"
    LIFT_DOWN = 0.1, "电梯下降"
    LIFT_DECELERATE = 0.2, "电梯减速"
    MANUAL_SPEED = 0.3, "手动速度"
    LIFT_LIGHT = 0.4, "电梯灯(闪为运行，常亮为故障)"
    LIFT_BRAKE = 0.5, "电梯刹车"
    START = 0.6, "启动"
    RUN_LIGHT = 0.7, "运行灯"
    TASK_TIMEOUT = 1.0, "任务超时"
    NO_FOREIGN_OBJECT = 1.1, "无异物"
    GIVEN_TARGET_LAYER = 2, "给定目标层"
    CARGO_STATUS = 4, "货物状态"
    LAYER_COUNT = 6, "层数"
    SPEED = 8, "速度"
    WORK_STEP = 10, "工作步"
    TARGET_LAYER_T = 12, "目标层"
    FAULT_T = 14, "故障"

class DB_2(PLCAddressBase, Enum):
    """
    [DB 2] - PLC点位地址枚举, 根据EXCEL点位表生成
    """
    def __init__(self, address, description):
        # 这里可以添加额外的初始化代码，例如验证地址格式
        self._value_ = address
        self._description = description # 自定义属性
    
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
    
    REMOTE_ONLINE = 0.2, "远程联机"
    CONVEYOR_ONLINE = 148.1, "输送线自动"


class LIFT_TASK_TYPE:
    """
    [电梯操作所需的任务类型]
        GOOD: 载货
        CAR: 载车
        IDEL: 空载
    """
    GOOD = 1
    CAR = 2
    GOOD_CAR = 3
    IDEL = 4

class FLOOR_CODE:
    """
    [PLC工位代号]
        GATE: 出入库口 输送线
        LIFT: 电梯 输送线
        LAYER_1: 1楼 接驳位输送线
        LAYER_2: 2楼 接驳位输送线
        LAYER_3: 3楼 接驳位输送线
        LAYER_4: 4楼 接驳位输送线
    """
    GATE = 1010
    LIFT = 1020
    LAYER_1 = 1030
    LAYER_2 = 1040
    LAYER_3 = 1050
    LAYER_4 = 1060


# 使用示例
if __name__ == "__main__":
    # 访问整型点位
    print(f"{DB_11.SCAN_CODE_RD.name} - {DB_11.SCAN_CODE_RD.value} - {DB_11.SCAN_CODE_RD.description}")  # 输出: 2 (int类型)
    
    # 访问浮点型点位
    print(f"{DB_12.FEED_COMPLETE_1010.name} - {DB_12.FEED_COMPLETE_1010.value} - {DB_12.FEED_COMPLETE_1010.description}")  # 输出: 22.0 (float类型)
    
    # 检查点位类型
    address = DB_11.STATUS_1010
    if address.is_float_address():
        print(f"{address.name} 是布尔点位")
    else:
        print(f"{address.name} 是数值点位")