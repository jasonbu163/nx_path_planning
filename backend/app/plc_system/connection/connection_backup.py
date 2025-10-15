# /devices/plc_service_old.py

from snap7.client import Client
from typing import Optional
from dataclasses import dataclass
import time
import re
import logging
logger = logging.getLogger(__name__)

@dataclass
class PLCConfig:
    max_retries: int = 3
    retry_delay: float = 1.0
    default_db_block: int = 12
    hex_pattern: str = r'^[0-9A-Fa-f]+(?: [0-9A-Fa-f]+)*$'

class PLCService:
    def __init__(self, ip: str, config: Optional[PLCConfig] = None):
        self.ip = ip
        self.config = config or PLCConfig()
        self.client = Client()
        self._connected = False

    def connect(self) -> bool:
        try:
            self.client.connect(self.ip, 0, 1)
            self._connected = self.client.get_connected()
            logger.info(f"🔌 Connected to PLC at {self.ip}")
        except Exception as e:
            logger.error(f"❌ PLC connection failed: {e}")
            self._connected = False
        return self._connected

    def _ensure_connection(self):
        if not self._connected or not self.client.get_connected():
            logger.warning("⚠️ PLC disconnected, attempting reconnect...")
            self.connect()

    def read_db(self, db_number: int, start: int, size: int) -> bytes:
        self._ensure_connection()
        for attempt in range(self.config.max_retries):
            try:
                data = self.client.db_read(db_number, start, size)
                return data
            except Exception as e:
                logger.warning(f"读失败 第{attempt+1}次: {e}")
                time.sleep(self.config.retry_delay)
        raise ConnectionError("读取 PLC DB 数据失败")

    def write_task(self, task_code: str, hex_command: str, db: Optional[int] = None, start: int = 0):
        """
        向 PLC 写入任务指令
        hex_command: str 或 bytes，例如 "01 02 03" 或 b'\x01\x02\x03'
        """
        self._ensure_connection()

        if isinstance(hex_command, str):
            hex_command = hex_command.strip()
            if not re.fullmatch(self.config.hex_pattern, hex_command):
                raise ValueError("报文格式非法，必须是空格分隔的十六进制字符")
            byte_data = bytes.fromhex(hex_command)
        elif isinstance(hex_command, bytes):
            byte_data = hex_command
        else:
            raise TypeError("hex_command 必须是 str 或 bytes")

        target_db = db or self.config.default_db_block

        for attempt in range(self.config.max_retries):
            try:
                self.client.db_write(target_db, start, byte_data)
                logger.info(f"✅ 写入 PLC 成功，任务: {task_code}, 长度: {len(byte_data)} bytes")
                return True
            except Exception as e:
                logger.error(f"❌ 写入失败 第{attempt+1}次: {e}")
                time.sleep(self.config.retry_delay)

        raise ConnectionError("写入 PLC 任务失败")
