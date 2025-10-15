# tests/test_task.py
# 系统路径
import os
import sys
from pathlib import Path
# 调试输出路径信息
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))

from task_scheduler import TaskScheduler

def main():
    ts = TaskScheduler()
    print(ts.node_status)
    ts.init_node_status()
    print(ts.node_status)

if __name__ == "__main__":
    main()