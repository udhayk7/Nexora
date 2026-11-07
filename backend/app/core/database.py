from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

from app.core.config import settings
from app.models.base import Base


def create_db_engine(database_url: str, is_test: bool = False, echo: bool = False) -> Engine:
    """Create an engine with pooling appropriate for the environment."""
    if database_url.startswith("sqlite"):
        if ":memory:" in database_url:
            return create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=echo,
            )
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
            echo=echo,
        )

    # PostgreSQL / Standard RDBMS
    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "echo": echo,
    }

    if settings.DB_SSL_MODE and not is_test:
        engine_kwargs["connect_args"] = {"sslmode": settings.DB_SSL_MODE}

    if is_test:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs.update(
            {
                "poolclass": QueuePool,
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "pool_recycle": settings.DB_POOL_RECYCLE,
            }
        )

    return create_engine(database_url, **engine_kwargs)


# Active application engine & sessionmaker
engine = create_db_engine(
    database_url=settings.DATABASE_URL,
    is_test=settings.is_test,
    echo=settings.DB_ECHO,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Request-safe FastAPI dependency yielding a managed database session."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


__all__ = ["Base", "engine", "SessionLocal", "get_db", "create_db_engine"]
