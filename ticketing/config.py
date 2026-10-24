"""Configuration: DB path resolution and field length limits (A-06, FR-017)."""

from __future__ import annotations

import os
from pathlib import Path

from ticketing.exceptions import DatabaseError

DB_ENV_VAR = "TICKETS_DB_PATH"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "data" / "tickets.db"

TITLE_MAX = 100
DESCRIPTION_MAX = 2000
CREATOR_MAX = 100
RESOLUTION_NOTE_MAX = 2000
SEARCH_MAX = 100


def get_db_path() -> Path:
    """Return the SQLite file path: ``TICKETS_DB_PATH`` env var or ``<repo>/data/tickets.db``.

    The parent directory is created if missing. No secrets are involved.
    """
    raw = os.environ.get(DB_ENV_VAR)
    try:
        path = Path(raw).expanduser() if raw else DEFAULT_DB_PATH
        parent = path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except (OSError, RuntimeError) as exc:
        raise DatabaseError() from exc
    return path
