# models/init_locations.py
# 用于初始化Location列表

# 系统路径
import os
import sys
from pathlib import Path
# 调试输出路径信息
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from models.base_model import LocationList
from models.init_db import init_db
from sqlalchemy.orm import sessionmaker


# 加载地图配置
with open('data/map_config.json', 'r') as f:
    map_config = json.load(f)

# 特殊状态节点定义
HIGHWAY_NODES = [
    "4,1,4", "4,2,4", "4,3,4", "4,4,4", "4,5,4", "4,6,4", "4,7,4",
    "4,1,3", "4,2,3", "4,3,3", "4,4,3", "4,5,3", "4,6,3", "4,7,3",
    "4,1,2", "4,2,2", "4,3,2", "4,4,2", "4,5,2", "4,6,2", "4,7,2",
    "4,1,1", "4,2,1", "4,3,1", "4,4,1", "4,5,1", "4,6,1", "4,7,1"
]
LIFT_NODES = [
    "6,3,1", "6,3,2", "6,3,3", "6,3,4"
]

# 创建数据库会话
engine = init_db()
Session = sessionmaker(bind=engine)
session = Session()


# 清空现有数据
session.query(LocationList).delete()

# 生成location数据
locations = []
for idx, location in enumerate(map_config['nodes'], start=1):
    # 先检查lift节点
    if location in LIFT_NODES:
        status = "lift"
    # 再检查highway节点
    elif location in HIGHWAY_NODES:
        status = "highway"
    # 其他节点设为free
    else:
        status = "free"
        
    locations.append(LocationList(
        id=idx,
        location=location,
        status=status,
        pallet_id=None
    ))

# 批量插入数据
session.add_all(locations)
session.commit()
print(f"成功初始化{len(locations)}个库位数据")