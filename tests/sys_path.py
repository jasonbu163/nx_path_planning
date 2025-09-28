# tests/sys_path.py

import sys
from pathlib import Path


def setup_path() -> None:
    """添加系统路径。"""
    ROOT_DIR = str(Path(__file__).parent.parent)
    print(f"Root directory: {ROOT_DIR}")
    sys.path.append(ROOT_DIR)