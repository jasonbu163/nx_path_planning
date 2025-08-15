# /config.py
PLC_IP = "192.168.8.10"
CAR_IP = "192.168.8.20"
CAR_PORT = 2504
SQLITE_DB = "wcs.db"
DB_PATH = "sqlite:///./data/wcs.db"

MAP_SIZE = 5

# 切换为 False 连接真实 PLC
USE_MOCK_PLC = True

# 等待设备执行动作完成的超时时间（秒）
PLC_ACTION_TIMEOUT = 120.0
CAR_ACTION_TIMEOUT = 300.0