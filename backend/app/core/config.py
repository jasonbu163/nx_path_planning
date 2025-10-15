# app/core/config.py

class Settings():

    # ===== 应用基础配置 =====
    PROJECT_NAME: str = "NetworkX Path Planning API"
    PROJECT_DESCRIPTION: str = "四向车立体库控制系统，支持入库、出库及库内移动任务的设备操作"
    PROJECT_VERSION: str = "2.2.2"

    # ===== 版本API添加前缀 =====
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"

    # ===== 服务器配置 =====
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ===== 设备配置 =====
    PLC_IP = "192.168.8.10"
    CAR_IP = "192.168.8.20"
    CAR_PORT = 2504

    # ====== 数据库配置 =====
    SQLITE_DB = "wcs.db"
    DATABASE_URL = f"sqlite:///./app/data/{SQLITE_DB}"

    # ===== 最大连接数 =====
    MAP_SIZE = 5

    # 切换为 False 连接真实 PLC
    USE_MOCK_PLC = False
    MOCK_BOOL = False  # True 切换为成功模拟，False 切换为失败模拟

    # 等待设备执行动作完成的超时时间（秒）
    PLC_ACTION_TIMEOUT = 120.0
    CAR_ACTION_TIMEOUT = 300.0

settings = Settings()