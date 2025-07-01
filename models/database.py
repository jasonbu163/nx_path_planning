# /models/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import SQLITE_DB
# from config import SQLITE_DB

DATABASE_URL = f"sqlite:///./data/{SQLITE_DB}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 数据库会话生成器
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()