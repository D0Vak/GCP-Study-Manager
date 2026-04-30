import ssl

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _connect_args() -> dict:
    if "sqlite" in settings.database_url:
        return {"check_same_thread": False}
    if settings.db_ssl:
        # Neon / Supabase など外部 PostgreSQL は SSL 必須
        ctx = ssl.create_default_context()
        return {"ssl_context": ctx}
    return {}


engine = create_engine(settings.database_url, connect_args=_connect_args())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
