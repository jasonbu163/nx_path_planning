# /config.py
PLC_IP = "192.168.8.10"
CAR_IP = "192.168.8.20"
CAR_PORT = 5000
SQLITE_DB = "wcs.db"
DB_PATH = "sqlite:///./data/wcs.db"

MAP_SIZE = 5

# 切换为 False 连接真实 PLC
USE_MOCK_PLC = True