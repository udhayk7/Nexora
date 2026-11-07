from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.database import create_db_engine, get_db


def test_create_db_engine_sqlite() -> None:
    engine = create_db_engine("sqlite:///:memory:", is_test=True)
    assert engine.name == "sqlite"


def test_create_db_engine_postgres_params() -> None:
    engine = create_db_engine(
        "postgresql+psycopg://user:pass@localhost:5432/db",
        is_test=False,
    )
    assert engine.name == "postgresql"
    assert engine.pool.size() == 5  # default DB_POOL_SIZE


def test_get_db_session_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_session = MagicMock(spec=Session)
    mock_sessionmaker = MagicMock(return_value=mock_session)

    monkeypatch.setattr("app.core.database.SessionLocal", mock_sessionmaker)

    generator = get_db()
    session = next(generator)
    assert session == mock_session

    with pytest.raises(StopIteration):
        next(generator)

    mock_session.close.assert_called_once()


def test_get_db_rollback_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_session = MagicMock(spec=Session)
    mock_sessionmaker = MagicMock(return_value=mock_session)

    monkeypatch.setattr("app.core.database.SessionLocal", mock_sessionmaker)

    generator = get_db()
    session = next(generator)
    assert session == mock_session

    with pytest.raises(RuntimeError, match="Simulated route error"):
        generator.throw(RuntimeError("Simulated route error"))

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()
