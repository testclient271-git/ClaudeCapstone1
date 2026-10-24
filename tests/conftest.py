"""Shared fixtures. Tests never touch the real ``data/tickets.db`` (architecture section 8)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from ticketing import service
from ticketing.config import DB_ENV_VAR, DEFAULT_DB_PATH
from ticketing.models import Ticket

_REAL_DB_BEFORE = (
    DEFAULT_DB_PATH.exists(),
    DEFAULT_DB_PATH.stat().st_mtime_ns if DEFAULT_DB_PATH.exists() else 0,
)


@pytest.fixture(autouse=True)
def _isolate_db_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point TICKETS_DB_PATH at a per-test temp file so nothing can hit the real DB."""
    path = tmp_path / "env_default.db"
    monkeypatch.setenv(DB_ENV_VAR, str(path))
    return path


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Initialised temp SQLite database."""
    path = tmp_path / "test.db"
    service.init_database(path)
    return path


@pytest.fixture
def raw_conn(db_path: Path):
    """Raw sqlite3 connection to the temp DB (for constraint tests)."""
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


@pytest.fixture
def make_ticket(db_path: Path) -> Callable[..., Ticket]:
    """Factory creating tickets with sensible defaults."""

    def _make(**kw) -> Ticket:
        args = {
            "title": "Printer broken",
            "description": "Third floor printer jams",
            "category": "Hardware",
            "priority": "Medium",
            "creator": "alice",
        }
        args.update(kw)
        return service.create_ticket(db_path, **args)

    return _make


def real_db_state() -> tuple[bool, int]:
    """Return (exists, mtime_ns) of the real DB file."""
    if DEFAULT_DB_PATH.exists():
        return True, DEFAULT_DB_PATH.stat().st_mtime_ns
    return False, 0


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ANN001
    """Fail the run loudly if the real database was created or modified."""
    if real_db_state() != _REAL_DB_BEFORE:
        session.exitstatus = 1
        print("\nSAFETY GUARD: real data/tickets.db was created or modified by the tests!")
