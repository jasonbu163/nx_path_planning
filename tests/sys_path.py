# tests/sys_path.py

import sys
from pathlib import Path


def setup_path() -> None:
    """
    [添加系统路径]
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))