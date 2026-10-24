"""Public service-layer contract used by the UI (architecture section 5.3).

FROZEN INTERFACE: signature changes need re-approval. Every function takes ``db_path``
first. Status/priority/category parameters accept enum members or their string values;
unknown values raise ``ValidationError``. Each mutating call is a single transaction.
"""

from __future__ import annotations

from pathlib import Path

from ticketing import db, repository, validation
from ticketing.exceptions import DatabaseError, TicketNotFoundError
from ticketing.models import (
    ALLOWED_TRANSITIONS,
    Category,
    DashboardStats,
    Priority,
    Status,
    Ticket,
    TicketFilter,
)

__all__ = [
    "allowed_next_statuses",
    "create_ticket",
    "get_dashboard_stats",
    "get_ticket",
    "init_database",
    "list_tickets",
    "list_tickets_for_creator",
    "update_priority",
    "update_resolution_note",
    "update_status",
]

PathLike = str | Path


def _coerce_filter(flt: TicketFilter | None) -> TicketFilter | None:
    """Return a filter whose status/priority/category are enum members (FR-006)."""
    if flt is None:
        return None
    return TicketFilter(
        status=validation.coerce_status(flt.status) if flt.status is not None else None,
        priority=validation.coerce_priority(flt.priority) if flt.priority is not None else None,
        category=validation.coerce_category(flt.category) if flt.category is not None else None,
        search=flt.search,
    )


def init_database(db_path: PathLike) -> None:
    """Create the schema if missing and set user_version (FR-017, NFR-003).

    Raises:
        DatabaseError: on any database failure or unsupported newer schema version.
    """
    db.init_db(db_path)


def create_ticket(
    db_path: PathLike,
    title: str,
    description: str,
    category: Category | str,
    priority: Priority | str,
    creator: str,
) -> Ticket:
    """Create a ticket with status Open, created_at == updated_at, no note (FR-001..004).

    Raises:
        ValidationError: any field missing, blank, too long or not in its allowed list
            (AC-001..006).
    """
    clean_title = validation.validate_title(title)
    clean_desc = validation.validate_description(description)
    cat = validation.coerce_category(category)
    prio = validation.coerce_priority(priority)
    clean_creator = validation.validate_creator(creator)
    now = repository.now_utc_iso()
    with db.transaction(db_path) as conn:
        new_id = repository.insert_ticket(
            conn, clean_title, clean_desc, cat, prio, clean_creator, now
        )
        ticket = repository.fetch_ticket(conn, new_id)
    if ticket is None:  # pragma: no cover - cannot happen inside one transaction
        raise DatabaseError()
    return ticket


def get_ticket(db_path: PathLike, ticket_id: int) -> Ticket:
    """Return one ticket (FR-007, AC-011/012).

    Raises:
        ValidationError: ``ticket_id`` is not a positive integer.
        TicketNotFoundError: no such ticket.
    """
    tid = validation.validate_ticket_id(ticket_id)
    with db.connect(db_path) as conn:
        ticket = repository.fetch_ticket(conn, tid)
    if ticket is None:
        raise TicketNotFoundError(tid)
    return ticket


def list_tickets(db_path: PathLike, filter: TicketFilter | None = None) -> list[Ticket]:
    """Return all matching tickets, newest first (``created_at DESC, id DESC``) (FR-006).

    Raises:
        DatabaseError: on database failure.
    """
    flt = _coerce_filter(filter)
    search = validation.validate_search(filter.search) if filter else None
    with db.connect(db_path) as conn:
        return repository.query_tickets(conn, flt, None, search)


def list_tickets_for_creator(db_path: PathLike, creator: str) -> list[Ticket]:
    """Return tickets whose trimmed creator equals ``creator`` case-insensitively (FR-005).

    Newest first.

    Raises:
        ValidationError: ``creator`` is blank.
    """
    name = validation.validate_creator(creator)
    with db.connect(db_path) as conn:
        return repository.query_tickets(conn, None, name, None)


def update_status(
    db_path: PathLike,
    ticket_id: int,
    new_status: Status | str,
    resolution_note: str | None = None,
) -> Ticket:
    """Change status per the transition table; refresh updated_at (FR-008, FR-010, FR-011).

    Resolved requires a non-blank note passed in or already stored (D-04). Same-status
    changes are rejected. The change is atomic (AC-014).

    Raises:
        ValidationError: invalid id, status or note.
        InvalidTransitionError: transition not allowed.
        TicketNotFoundError: no such ticket.
    """
    tid = validation.validate_ticket_id(ticket_id)
    requested = validation.coerce_status(new_status)
    note = validation.optional_resolution_note(resolution_note)
    now = repository.now_utc_iso()
    with db.transaction(db_path) as conn:
        current = repository.fetch_ticket(conn, tid)
        if current is None:
            raise TicketNotFoundError(tid)
        validation.check_transition(current.status, requested)
        note = validation.require_note_for_resolved(requested, note, current.resolution_note)
        if note is None:
            repository.update_ticket_fields(conn, tid, now=now, status=requested)
        else:
            repository.update_ticket_fields(
                conn, tid, now=now, status=requested, resolution_note=note
            )
        updated = repository.fetch_ticket(conn, tid)
    if updated is None:  # pragma: no cover - cannot happen inside one transaction
        raise DatabaseError()
    return updated


def update_priority(db_path: PathLike, ticket_id: int, new_priority: Priority | str) -> Ticket:
    """Change priority; refresh updated_at (FR-009, FR-011, AC-015).

    Raises:
        ValidationError: invalid id or priority.
        TicketNotFoundError: no such ticket.
    """
    tid = validation.validate_ticket_id(ticket_id)
    prio = validation.coerce_priority(new_priority)
    now = repository.now_utc_iso()
    with db.transaction(db_path) as conn:
        if not repository.update_ticket_fields(conn, tid, now=now, priority=prio):
            raise TicketNotFoundError(tid)
        updated = repository.fetch_ticket(conn, tid)
    if updated is None:  # pragma: no cover - cannot happen inside one transaction
        raise DatabaseError()
    return updated


def update_resolution_note(db_path: PathLike, ticket_id: int, note: str) -> Ticket:
    """Add or edit the resolution note in any status; refresh updated_at (FR-021, AC-030).

    Blank notes are rejected (D-04).

    Raises:
        ValidationError: invalid id, blank or too-long note.
        TicketNotFoundError: no such ticket.
    """
    tid = validation.validate_ticket_id(ticket_id)
    clean_note = validation.validate_resolution_note(note)
    now = repository.now_utc_iso()
    with db.transaction(db_path) as conn:
        if not repository.update_ticket_fields(conn, tid, now=now, resolution_note=clean_note):
            raise TicketNotFoundError(tid)
        updated = repository.fetch_ticket(conn, tid)
    if updated is None:  # pragma: no cover - cannot happen inside one transaction
        raise DatabaseError()
    return updated


def get_dashboard_stats(db_path: PathLike) -> DashboardStats:
    """Return status, priority and category counts computed in SQL (FR-012..016, FR-020).

    Raises:
        DatabaseError: on database failure.
    """
    with db.connect(db_path) as conn:
        by_status = repository.count_by_status(conn)
        by_prio = repository.count_by_priority(conn)
        by_cat = repository.count_by_category(conn)
    return DashboardStats(
        total=sum(by_status.values()),
        open=by_status.get(Status.OPEN.value, 0),
        in_progress=by_status.get(Status.IN_PROGRESS.value, 0),
        resolved=by_status.get(Status.RESOLVED.value, 0),
        closed=by_status.get(Status.CLOSED.value, 0),
        by_priority={p: by_prio.get(p.value, 0) for p in Priority},
        by_category={c: by_cat.get(c.value, 0) for c in Category},
    )


def allowed_next_statuses(current: Status | str) -> list[Status]:
    """Return statuses reachable from ``current``, in enum order (FR-010, D-02).

    Pure helper for UI dropdowns; Closed yields an empty list.

    Raises:
        ValidationError: ``current`` is not a valid status.
    """
    cur = validation.coerce_status(current)
    return [s for s in Status if s in ALLOWED_TRANSITIONS[cur]]
