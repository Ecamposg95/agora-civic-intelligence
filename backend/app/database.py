"""Database engine, session factory and declarative base (SQLAlchemy 2.0)."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
_connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # Local/dev convenience: share one connection across the threadpool.
    from sqlalchemy.pool import StaticPool

    _connect_args["check_same_thread"] = False
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
