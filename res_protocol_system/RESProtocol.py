# car_control/RESprotocol.py
from enum import IntEnum

# ------------------------
# 模块 1: 协议定义与常量
# 职责: 定义协议相关常量、枚举和结构
# 维护者: 协议专家
# ------------------------

class RESProtocol:
    """协议常量定义"""
    HEADER = b'\x02\xfd'
    FOOTER = b'\x03\xfc'
    VERSION = 0x01  # 版本1.0
    HEARTBEAT_INTERVAL = 0.6    # 心跳间隔600ms

    class FrameType(IntEnum):
        """报文类型枚举"""
        HEARTBEAT = 0
        TASK = 1
        COMMAND = 2
        DEBUG = 3
        FILE_TRANSFER = 4
        SCADA = 5
        LORA_CONFIG = 6
        HEARTBEAT_WITH_BATTERY = 10  # 带电量心跳

    class CarStatus(IntEnum):
        """车辆状态枚举"""
        TASK_EXECUTING = 1
        COMMAND_EXECUTING = 2
        READY = 3
        PAUSED = 4
        CHARGING = 5
        FAULT = 6
        SLEEPING = 7
        NODE_STANDBY = 11

    class CommandID(IntEnum):
        """指令码枚举"""
        EMERGENCY_STOP = 0x81
        PAUSE_RESUME = 0x82
        CHANGE_SPEED = 0x83
        SET_SEGMENT = 0x90
        QUERY_PALLET = 0x91
        SET_FLOOR = 0x92
        SLEEP = 0x96
        WAKE_UP = 0x97
        SEND_MAP = 0x98
        GET_BATTERY = 0x99
        SET_PARAM = 0x9D
        GET_PARAM = 0x9E
        GET_VERSION = 0xA0

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