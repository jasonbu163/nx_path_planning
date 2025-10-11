# app/utils/logger.py
import os
from pathlib import Path
from typing import Optional

import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    """设置日志"""
    # 创建日志目录
    logs_dir = Path("app/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 主logger配置
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt='[%(asctime)s - %(name)s - %(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        fmt='[%(asctime)s - %(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 通用日志文件处理器（记录所有日志）
    all_handler = RotatingFileHandler(
        filename=os.path.join(logs_dir, "all.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    all_handler.setLevel(logging.DEBUG)
    all_handler.setFormatter(file_formatter)

    # 错误日志文件处理器（仅记录 ERROR 级别及以上的日志）
    error_handler = RotatingFileHandler(
        filename=os.path.join(logs_dir, "error.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    # 控制台日志处理器（仅显示 INFO 及以上级别的日志）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # 清除旧处理器
    logger.handlers.clear()

    # 添加处理器
    logger.addHandler(all_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)