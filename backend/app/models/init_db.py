# app/models/init_db.py

from sqlalchemy import create_engine

from app.core import DeclarativeBase, settings
# 初始化数据库
def init_db(db_url=settings.DATABASE_URL, echo=False):
    """初始化数据库并创建表结构。
    
    Args:
        db_url: 数据库连接字符串，默认为SQLite
        echo: 是否显示SQL语句，默认为False
    """
    engine = create_engine(db_url, echo=echo)
    print(f"正在创建数据库表结构({db_url})...")
    DeclarativeBase.metadata.create_all(engine)
    print("数据库表结构创建完成!")
    return engine