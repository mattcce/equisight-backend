from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from typing import AsyncGenerator

SQLALCHEMY_DATABASE_URL = "sqlite:///equisight-backend.db"
ASYNC_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///equisight-backend.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async enginge for FastAPI users
async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)
async_session_maker = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Async session for FastAPI users
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
