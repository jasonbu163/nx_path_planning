# models/init_db.py

# 系统路径
import os
import sys
from pathlib import Path
# 调试输出路径信息
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_PATH
from sqlalchemy import create_engine

from models.base_model import Base
# 初始化数据库
def init_db(db_url=DB_PATH, echo=False):
    """
    初始化数据库并创建表结构
    
    参数:
        db_url: 数据库连接字符串，默认为SQLite
        echo: 是否显示SQL语句，默认为False
    """
    engine = create_engine(db_url, echo=echo)
    print(f"正在创建数据库表结构({db_url})...")
    Base.metadata.create_all(engine)
    print("数据库表结构创建完成!")
    return engine

if __name__ == "__main__":
    init_db()