# devices/car_enum.py
from enum import Enum

class CarBaseEnum(Enum):
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
    
class RESProtocol(CarBaseEnum):
    """
    [报文常用变量定义]
    """
    HEADER = b'\x02\xfd', "报文头"
    FOOTER = b'\x03\xfc', "报文尾"
    VERSION = 1, "版本号"
    HEARTBEAT_INTERVAL = 0.6, "心跳间隔"

class FrameType(CarBaseEnum):
    """
    [报文类型]
    """
    HEARTBEAT = 0, "心跳"
    TASK = 1, "任务"
    COMMAND = 2, "交互指令"
    DEBUG = 3, "调试"
    FILE_TRANSFER = 4, "文件传输"
    SCADA = 5, "SCADA"
    LORA_CONFIG = 6, "LoRa配置"
    HEARTBEAT_WITH_BATTERY = 10, "带电量心跳"
    
######################
###### 穿梭车状态 #####
#####################
class CarStatus(CarBaseEnum):
    """
    [接收 - 穿梭车状态码] - 用于解析返回报文中状态信息
    """
    TASK_EXECUTING = 1, "任务执行中"
    COMMAND_EXECUTING = 2, "命令执行中"
    READY = 3, "就绪"
    PAUSED = 4, "暂停"
    CHARGING = 5, "充电中"
    FAULT = 6, "故障"
    SLEEPING = 7, "休眠状态"
    NODE_STANDBY = 11, "节点待命"

    @classmethod
    def get_by_value(cls, value):
        """
        根据值获取枚举成员
        """
        for member in cls:
            if member.value == value:
                return member
        return None
    
    @classmethod
    def get_info_by_value(cls, value) -> dict:
        """
        根据值获取枚举成员的名称和描述
        """
        member = cls.get_by_value(value)
        if member:
            return {
                'name': member.name,
                'description': member.description
            }
        return {
            'name': 'UNKNOWN',
            'description': '未知'
        }


##########################
###### 穿梭车 工作指令 #####
#########################
class WorkCommand(CarBaseEnum):
    """
    [发送 - 工作指令码] - 用于发送工作指令
    """
    PALLET_PICKUP = b'\x01', "托盘取货"
    PALLET_PLACE = b'\x02', "托盘放货"
    START_CHARGING = b'\x03', "开始充电"
    STOP_CHARGING = b'\x04', "关闭充电"
    SWITCH_TO_RAMP = b'\x05', "换向到坡道"
    SWITCH_TO_ALLEY = b'\x06', "换向到巷道"
    PALLET_CALIBRATION = b'\x08', "托盘校准"
    PALLET_CALIBRATION_AND_LIFT = b'\x09', "托盘校准+托盘顶升"
    MOVE_DIRECTION_1_DISTANCE = b'\x11', "按1方向距离行驶"
    MOVE_DIRECTION_2_DISTANCE = b'\x12', "按2方向距离行驶"
    MOVE_DIRECTION_3_DISTANCE = b'\x13', "按3方向距离行驶"
    MOVE_DIRECTION_4_DISTANCE = b'\x14', "按4方向距离行驶"
    TIME_SYNC = b'\x15', "时间同步"
    MOVE_DIRECTION_1_AT_SPEED = b'\x41', "按1方向速度行驶"
    MOVE_DIRECTION_2_AT_SPEED = b'\x42', "按2方向速度行驶"
    MOVE_DIRECTION_3_AT_SPEED = b'\x43', "按3方向速度行驶"
    MOVE_DIRECTION_4_AT_SPEED = b'\x44', "按4方向速度行驶"
    OIL_PUMP_FORWARD_AT_SPEED = b'\x45', "油泵按速度正转"
    OIL_PUMP_REVERSE_AT_SPEED = b'\x46', "油泵按速度反转"
    UPDATE_CAR_COORDINATES = b'\x50', "更改穿梭车车坐标"
    MANUAL_POSITION_CALIBRATION = b'\x51', "手动校准位置"

##########################
###### 穿梭车 调试指令 #####
#########################
class ImmediateCommand(CarBaseEnum):
    """
    [发送 - 即时指令码] - 用于发送即时指令
    """
    # 穿梭车急停 - 紧急停止穿梭车当前的行驶
    EMERGENCY_STOP = b'\x81', "穿梭车急停"
    # 穿梭车暂停恢复 - 穿梭车在行驶暂停状态下时恢复行驶
    PAUSE_RESUME = b'\x82', "穿梭车暂停恢复"
    CHANGE_SPEED = b'\x83', "更改穿梭车行驶速度"
    CHANGE_SPEED_IN_SPECIAL_POSITION = b'\x84', "更改穿梭车特殊位置行驶速度"
    OPEN_BEEPER = b'\x85', "打开蜂鸣器"
    CLOSE_BEEPER = b'\x86', "关闭蜂鸣器"
    WORK_PAUSE = b'\x87', "行驶暂停"
    STOP_BY_SPEED = b'\x88', "小车按速度停止"
    OPEN_BRAKE = b'\x89', "打开刹车"
    CLOSE_BRAKE = b'\x8A', "关闭刹车"
    CLEAR_TURN_ERROR = b'\x8B', "清空转向驱动器错误"
    CLEAR_MOVE_DISTANCE = b'\x8C', "位移量清零"
    CLEAR_DRIVER_ERROR = b'\x8D', "清空行驶驱动器错误"
    # 初始化指令 - 初始化穿梭车的当前状态以及穿梭车内的任务
    INIT_COMMAND = b'\x8E', "初始化指令"
    # 任务撤销 - 撤销穿梭车当前已存在的任务，若穿梭车正在执行任务过程中则撤销失败
    CANCEL_TASK = b'\x8F', "任务撤销"
    # 下发段序号 - 给res下发行驶到那一段
    SET_SEGMENT_NO = b'\x90', "下发段序号"
    QUERY_PALLET = b'\x91', "查询穿梭车托盘有无"
    SET_FLOOR = b'\x92', "下发提升机当前层"
    SLEEP_SYSTEM = b'\x96', "穿梭车系统休眠"
    # 穿梭车系统唤醒
    WAKE_UP_SYSTEM = b'\x97', "穿梭车系统唤醒"
    SEND_MAP = b'\x98', "发送地图"
    GET_BATTERY = b'\x99', "获取电量指令"
    SET_PARAM = b'\x9D', "设置单个参数"
    GET_PARAM = b'\x9E', "获取单个参数"

class Debug(CarBaseEnum):
    """
    [调试指令] - 用于穿梭车的调试
    """
    # 获取RES全部参数 - 读取RES全部参数(不包含固件版本)
    GET_ALL_PARAM = b'\xA2', "获取RES全部参数"

class ErrorHandler:
    """错误码映射表"""
    ERROR_MAP = {
        0: ("成功", "无"),
        4161: ("KCS未返回执行结果", "检查小车电源和通讯线路"),
        12462: ("行驶系统总时间超时", "发送急停指令并检查小车状态"),
        12456: ("前方有托盘障碍物", "重新规划路径"),
        12457: ("前方有障碍物", "清理障碍物并重新下发指令"),
        8404: ("压到限位开关", "检查换向机构"),
        # 添加更多错误码...
        3001: ("充电失败", "检查充电连接"),
        3002: ("电池温度过高", "暂停使用"),
    }

    @classmethod
    def get_error_info(cls, error_code):
        return cls.ERROR_MAP.get(error_code, (f"未知错误: {error_code}", "联系技术支持"))
    
    @classmethod
    def is_critical_error(cls, error_code):
        """是否为关键错误"""
        return error_code >= 4000   #4000以上的错误为关键错误
    

if __name__ == "__main__":
    
    # 测试枚举类
    for status in WorkCommand:
        print(f"{status.name}: {status.value} - {status.description}")
    
    print(ImmediateCommand.CANCEL_TASK.value)