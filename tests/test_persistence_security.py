"""Persistence, injection, schema constraints, performance (FR-017, NFR-003..005, AC-021..026)."""

import sqlite3
import time

import pytest

from ticketing import db, service
from ticketing.exceptions import DatabaseError
from ticketing.models import Priority, TicketFilter

INJECTIONS = [
    "'; DROP TABLE tickets;--",
    "\" OR \"1\"=\"1",
    "x' OR '1'='1",
    "Robert'); DROP TABLE tickets;--",
    "1; DELETE FROM tickets",
    "%' UNION SELECT * FROM tickets --",
]


@pytest.mark.req("FR-017", "NFR-003", "AC-021")
def test_persistence_across_connections_ac021(db_path, make_ticket):
    t = make_ticket(title="Persist me", description="desc")
    service.update_resolution_note(db_path, t.id, "the note")
    service.update_priority(db_path, t.id, "Critical")
    again = service.get_ticket(db_path, t.id)
    assert again.title == "Persist me" and again.resolution_note == "the note"
    assert again.priority is Priority.CRITICAL
    with sqlite3.connect(db_path) as c:
        assert c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 1


@pytest.mark.req("FR-017", "NFR-003", "AC-021")
def test_init_database_idempotent_keeps_data_ac021(db_path, make_ticket):
    t = make_ticket()
    service.init_database(db_path)
    service.init_database(db_path)
    assert service.get_ticket(db_path, t.id) == t
    with sqlite3.connect(db_path) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 1


@pytest.mark.req("FR-017", "NFR-003")
def test_init_creates_missing_file(tmp_path):
    p = tmp_path / "new.db"
    assert not p.exists()
    service.init_database(p)
    assert p.exists()
    assert service.list_tickets(p) == []


@pytest.mark.req("FR-017")
def test_init_rejects_newer_schema_version(tmp_path):
    p = tmp_path / "future.db"
    with sqlite3.connect(p) as c:
        c.execute("PRAGMA user_version = 99")
    with pytest.raises(DatabaseError):
        service.init_database(p)


@pytest.mark.req("NFR-004")
def test_database_error_wrapped_not_raw_sqlite(tmp_path):
    bad = tmp_path / "no_such_dir" / "x.db"
    with pytest.raises(DatabaseError):
        service.list_tickets(bad)


@pytest.mark.req("NFR-004", "AC-025")
@pytest.mark.parametrize("payload", INJECTIONS)
def test_sql_injection_stored_literally_ac025(db_path, payload):
    t = service.create_ticket(
        db_path, payload[:100], payload, "Other", "Low", payload[:100]
    )
    got = service.get_ticket(db_path, t.id)
    assert got.title == payload[:100].strip() and got.description == payload.strip()
    service.update_resolution_note(db_path, t.id, payload)
    assert service.get_ticket(db_path, t.id).resolution_note == payload.strip()
    # table intact and filters/creator lookups are safe
    assert len(service.list_tickets(db_path)) == 1
    assert len(service.list_tickets_for_creator(db_path, payload[:100])) == 1
    assert service.list_tickets(db_path, TicketFilter(search=payload))[0].id == t.id
    other = service.create_ticket(db_path, "other", "other", "Other", "Low", "zed")
    assert service.list_tickets_for_creator(db_path, "zed")[0].id == other.id
    assert service.get_dashboard_stats(db_path).total == 2


@pytest.mark.req("NFR-004", "AC-025")
def test_injection_in_enum_fields_rejected_not_executed(db_path, make_ticket):
    from ticketing.exceptions import ValidationError

    with pytest.raises(ValidationError):
        service.create_ticket(db_path, "t", "d", "Other'; DROP TABLE tickets;--", "Low", "x")
    t = make_ticket()
    with pytest.raises(ValidationError):
        service.update_status(db_path, t.id, "Open'; DROP TABLE tickets;--")
    assert len(service.list_tickets(db_path)) == 1


_COLS = (
    "title, description, category, priority, status, creator, created_at, updated_at, "
    "resolution_note"
)


def _raw_insert(conn, **over):
    row = {
        "title": "t", "description": "d", "category": "Other", "priority": "Low",
        "status": "Open", "creator": "c", "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z", "resolution_note": None,
    }
    row.update(over)
    conn.execute(
        f"INSERT INTO tickets ({_COLS}) VALUES (?,?,?,?,?,?,?,?,?)",
        tuple(row[c.strip()] for c in _COLS.split(",")),
    )


@pytest.mark.req("NFR-004")
def test_schema_accepts_valid_raw_insert(raw_conn):
    _raw_insert(raw_conn)


@pytest.mark.req("NFR-004")
@pytest.mark.parametrize(
    "over",
    [
        {"priority": "Urgent"},
        {"priority": "low"},
        {"status": "Done"},
        {"status": "open"},
        {"category": "Printers"},
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 101},
        {"description": ""},
        {"description": "x" * 2001},
        {"creator": " "},
        {"creator": "x" * 101},
        {"resolution_note": ""},
        {"resolution_note": "x" * 2001},
        {"created_at": "2025-02-01T00:00:00Z", "updated_at": "2025-01-01T00:00:00Z"},
        {"status": "Resolved", "resolution_note": None},
        {"status": "Closed", "resolution_note": None},
        {"title": None},
        {"created_at": None},
    ],
)
def test_schema_check_constraints_reject_bad_raw_insert(raw_conn, over):
    with pytest.raises(sqlite3.IntegrityError):
        _raw_insert(raw_conn, **over)


@pytest.mark.req("NFR-004")
def test_schema_check_rejects_bad_raw_update(raw_conn):
    _raw_insert(raw_conn)
    with pytest.raises(sqlite3.IntegrityError):
        raw_conn.execute("UPDATE tickets SET status='Nope'")
    with pytest.raises(sqlite3.IntegrityError):
        raw_conn.execute("UPDATE tickets SET status='Resolved'")  # no note


@pytest.mark.req("NFR-004")
def test_schema_enum_parity_with_models():
    from ticketing.models import Category, Status

    for enum in (Category, Priority, Status):
        for m in enum:
            assert f"'{m.value}'" in db.SCHEMA_DDL
    assert db.SCHEMA_DDL.count("CHECK (category IN") == 1


@pytest.mark.req("NFR-004")
def test_corrupt_enum_value_in_db_becomes_database_error(db_path):
    with sqlite3.connect(db_path) as c:
        c.execute("PRAGMA ignore_check_constraints = ON")
        _raw_insert(c, priority="Bogus")
    with pytest.raises(DatabaseError):
        service.list_tickets(db_path)


@pytest.mark.req("NFR-005", "AC-026")
def test_performance_1000_tickets_ac026(db_path):
    with sqlite3.connect(db_path) as c:
        for i in range(1000):
            _raw_insert(c, title=f"t{i}", priority=list(Priority)[i % 4].value)
    t0 = time.perf_counter()
    assert len(service.list_tickets(db_path)) == 1000
    t_list = time.perf_counter() - t0
    t0 = time.perf_counter()
    assert service.get_dashboard_stats(db_path).total == 1000
    t_dash = time.perf_counter() - t0
    assert t_list < 2.0 and t_dash < 2.0
