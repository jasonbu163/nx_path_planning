# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

db_url = settings.DATABASE_URL
engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {}
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DeclarativeBase = declarative_base()

def get_db():
    """数据库会话生成器。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()