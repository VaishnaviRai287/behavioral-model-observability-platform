from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


# The engine is the core connection pool to PostgreSQL.
# It handles connection pooling, reconnection, etc.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # test connections before using them
    pool_size=5,          # maintain 5 persistent connections
    max_overflow=10,      # allow 10 extra connections under load
)

# SessionLocal is a factory: calling SessionLocal() gives you one DB session.
# A session is a unit of work — you open it, do DB operations, then close it.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base is the parent class all ORM models inherit from.
# It keeps a registry of all tables so Alembic can find them.
class Base(DeclarativeBase):
    pass


# This is a FastAPI dependency — it yields a session and always closes it.
def get_db():
    db = SessionLocal()
    try:
        yield db       # FastAPI injects this into route handlers
    finally:
        db.close()    # always runs, even if an exception occurred
