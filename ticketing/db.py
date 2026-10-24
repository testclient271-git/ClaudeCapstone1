"""SQLite connection helper and schema bootstrap (FR-017, NFR-003, NFR-004).

Every call opens a short-lived connection (architecture D-05). Raw ``sqlite3.Error``
instances never leave this package: they are converted to ``DatabaseError`` with a
generic message and the original exception chained.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from ticketing.exceptions import DatabaseError

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
BUSY_TIMEOUT_SECONDS = 5.0

# Must stay identical to the enum values in models.py (NFR-004; QA parity test).
SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 100),
    description     TEXT    NOT NULL CHECK (length(trim(description)) BETWEEN 1 AND 2000),
    category        TEXT    NOT NULL
                            CHECK (category IN ('Hardware','Software','Network','Access','Other')),
    priority        TEXT    NOT NULL CHECK (priority IN ('Low','Medium','High','Critical')),
    status          TEXT    NOT NULL DEFAULT 'Open'
                            CHECK (status IN ('Open','In Progress','Resolved','Closed')),
    creator         TEXT    NOT NULL CHECK (length(trim(creator)) BETWEEN 1 AND 100),
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    resolution_note TEXT    NULL
                            CHECK (resolution_note IS NULL
                                   OR length(trim(resolution_note)) BETWEEN 1 AND 2000),
    CHECK (updated_at >= created_at),
    CHECK (status NOT IN ('Resolved','Closed') OR resolution_note IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_tickets_creator_nocase ON tickets (creator COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_tickets_status   ON tickets (status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets (priority);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets (category);
"""

_SET_VERSION_SQL = "PRAGMA user_version = 1"  # PRAGMA cannot be parameterized; constant only.


def _wrap(exc: sqlite3.Error) -> DatabaseError:
    """Log the error class (never ticket text) and return a generic ``DatabaseError``."""
    logger.error("Database error: %s", type(exc).__name__)
    return DatabaseError()


def _unicode_nocase(a: str, b: str) -> int:
    """Collation comparing NFC-normalised, casefolded strings (Unicode-aware, F-05)."""
    x = unicodedata.normalize("NFC", a).casefold()
    y = unicodedata.normalize("NFC", b).casefold()
    return (x > y) - (x < y)


def _open(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection with row factory and foreign keys on (manual transaction control)."""
    path = Path(db_path)
    is_new = str(db_path) != ":memory:" and not path.exists()
    if is_new:
        try:  # best effort: create the DB file owner-only (F-10)
            os.close(os.open(path, os.O_CREAT | os.O_WRONLY, 0o600))
        except OSError:
            pass
    conn = sqlite3.connect(str(db_path), timeout=BUSY_TIMEOUT_SECONDS, isolation_level=None)
    conn.create_collation("UNICODE_NOCASE", _unicode_nocase)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Yield a short-lived read connection and always close it (FR-017).

    Raises:
        DatabaseError: if the database cannot be opened or a query fails.
    """
    try:
        with closing(_open(db_path)) as conn:
            yield conn
    except sqlite3.Error as exc:
        raise _wrap(exc) from exc
    except OSError as exc:
        raise DatabaseError() from exc


@contextmanager
def transaction(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Yield a connection inside one write transaction: commit on success, else rollback.

    Uses ``BEGIN IMMEDIATE`` so read-check-write sequences are atomic (AC-014).

    Raises:
        DatabaseError: on any ``sqlite3.Error``; typed ticketing errors pass through
            after rollback.
    """
    try:
        with closing(_open(db_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    logger.error("Rollback failed")  # never mask the original exception
                raise
            conn.execute("COMMIT")
    except sqlite3.Error as exc:
        raise _wrap(exc) from exc
    except OSError as exc:
        raise DatabaseError() from exc


def init_db(db_path: str | Path) -> None:
    """Create the schema if missing and set ``user_version`` (idempotent; FR-017, NFR-003).

    Raises:
        DatabaseError: on database failure or if the file has a newer schema version.
    """
    try:
        with closing(_open(db_path)) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise DatabaseError("The database was created by a newer version of this app.")
            conn.executescript(SCHEMA_DDL)
            conn.execute(_SET_VERSION_SQL)
    except sqlite3.Error as exc:
        raise _wrap(exc) from exc
    except OSError as exc:
        raise DatabaseError() from exc
