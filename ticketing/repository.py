"""All SQL for tickets: static, parameterized statements only (NFR-004, AC-025).

Functions take an open ``sqlite3.Connection`` (from ``ticketing.db``) and return DTOs.
Filters use fixed SQL with ``? IS NULL OR ...`` patterns so no SQL text is ever built
from input. Errors are mapped to ``DatabaseError`` by ``ticketing.db`` context managers.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ticketing.exceptions import DatabaseError
from ticketing.models import Category, Priority, Status, Ticket, TicketFilter

_INSERT_SQL = (
    "INSERT INTO tickets (title, description, category, priority, status, creator, "
    "created_at, updated_at, resolution_note) VALUES (?, ?, ?, ?, 'Open', ?, ?, ?, NULL)"
)
_SELECT_ONE_SQL = (
    "SELECT id, title, description, category, priority, status, creator, "
    "created_at, updated_at, resolution_note FROM tickets WHERE id = ?"
)
_QUERY_SQL = (
    "SELECT id, title, description, category, priority, status, creator, "
    "created_at, updated_at, resolution_note FROM tickets "
    "WHERE (? IS NULL OR status = ?) "
    "AND (? IS NULL OR priority = ?) "
    "AND (? IS NULL OR category = ?) "
    "AND (? IS NULL OR creator COLLATE UNICODE_NOCASE = ?) "
    "AND (? IS NULL OR title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\') "
    "ORDER BY created_at DESC, id DESC"
)
_UPDATE_SQL = (
    "UPDATE tickets SET status = COALESCE(?, status), priority = COALESCE(?, priority), "
    "resolution_note = CASE WHEN ? THEN ? ELSE resolution_note END, "
    "updated_at = max(?, created_at) WHERE id = ?"
)
_COUNT_STATUS_SQL = "SELECT status, COUNT(*) AS n FROM tickets GROUP BY status"
_COUNT_PRIORITY_SQL = "SELECT priority, COUNT(*) AS n FROM tickets GROUP BY priority"
_COUNT_CATEGORY_SQL = "SELECT category, COUNT(*) AS n FROM tickets GROUP BY category"


class _Unset:
    """Sentinel type meaning 'leave resolution_note unchanged'."""


UNSET = _Unset()


def now_utc_iso() -> str:
    """Return the current UTC time as ``YYYY-MM-DDTHH:MM:SSZ`` (FR-004, FR-011)."""
    # timezone.utc kept on purpose: datetime.UTC requires Python 3.11+; baseline is 3.10+.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: UP017


def _to_ticket(row: sqlite3.Row) -> Ticket:
    """Map a row to a ``Ticket``; corrupted enum values become ``DatabaseError``."""
    try:
        return Ticket(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            category=Category(row["category"]),
            priority=Priority(row["priority"]),
            status=Status(row["status"]),
            creator=row["creator"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            resolution_note=row["resolution_note"],
        )
    except ValueError as exc:
        raise DatabaseError() from exc


def escape_like(term: str) -> str:
    """Escape backslash, percent and underscore so a search term is matched literally."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def insert_ticket(
    conn: sqlite3.Connection,
    title: str,
    description: str,
    category: Category,
    priority: Priority,
    creator: str,
    now: str,
) -> int:
    """Insert an Open ticket (created_at == updated_at) and return its id (FR-001, FR-004)."""
    cur = conn.execute(
        _INSERT_SQL, (title, description, category.value, priority.value, creator, now, now)
    )
    if cur.lastrowid is None:
        raise DatabaseError()
    return int(cur.lastrowid)


def fetch_ticket(conn: sqlite3.Connection, ticket_id: int) -> Ticket | None:
    """Return the ticket or ``None`` (FR-007)."""
    row = conn.execute(_SELECT_ONE_SQL, (ticket_id,)).fetchone()
    return _to_ticket(row) if row else None


def query_tickets(
    conn: sqlite3.Connection,
    flt: TicketFilter | None = None,
    creator: str | None = None,
    search: str | None = None,
) -> list[Ticket]:
    """Return matching tickets newest first (FR-005, FR-006).

    ``flt`` fields must already be coerced enums; ``creator`` is a trimmed exact,
    case-insensitive match; ``search`` is a literal substring over title/description.
    """
    status = flt.status.value if flt and flt.status else None
    priority = flt.priority.value if flt and flt.priority else None
    category = flt.category.value if flt and flt.category else None
    pattern = f"%{escape_like(search)}%" if search else None
    params = (
        status, status, priority, priority, category, category,
        creator, creator, pattern, pattern, pattern,
    )  # fmt: skip
    return [_to_ticket(r) for r in conn.execute(_QUERY_SQL, params).fetchall()]


def update_ticket_fields(
    conn: sqlite3.Connection,
    ticket_id: int,
    *,
    now: str,
    status: Status | None = None,
    priority: Priority | None = None,
    resolution_note: str | None | _Unset = UNSET,
) -> bool:
    """Update the given fields and ``updated_at``; return False if no row matched (FR-011)."""
    set_note = not isinstance(resolution_note, _Unset)
    note = None if isinstance(resolution_note, _Unset) else resolution_note
    cur = conn.execute(
        _UPDATE_SQL,
        (
            status.value if status else None,
            priority.value if priority else None,
            1 if set_note else 0,
            note,
            now,
            ticket_id,
        ),
    )
    return cur.rowcount > 0


def count_by_status(conn: sqlite3.Connection) -> dict[str, int]:
    """Return ticket counts keyed by status string (FR-012..014)."""
    return {r["status"]: r["n"] for r in conn.execute(_COUNT_STATUS_SQL)}


def count_by_priority(conn: sqlite3.Connection) -> dict[str, int]:
    """Return ticket counts keyed by priority string (FR-015)."""
    return {r["priority"]: r["n"] for r in conn.execute(_COUNT_PRIORITY_SQL)}


def count_by_category(conn: sqlite3.Connection) -> dict[str, int]:
    """Return ticket counts keyed by category string (FR-020)."""
    return {r["category"]: r["n"] for r in conn.execute(_COUNT_CATEGORY_SQL)}
