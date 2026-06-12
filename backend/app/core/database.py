from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Create engine with asyncpg driver (or aiosqlite for SQLite) for asynchronous database actions
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Logs executed SQL statements (disable in production)
    future=True,
    connect_args=connect_args
)

# Create a sessionmaker that generates AsyncSession instances
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Declarative base class for models
class Base(DeclarativeBase):
    pass