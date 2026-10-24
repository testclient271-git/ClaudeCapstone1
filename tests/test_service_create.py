"""Ticket creation and validation (FR-001..004, NFR-002, AC-001..006)."""

import sqlite3

import pytest

from ticketing import service
from ticketing.config import CREATOR_MAX, DESCRIPTION_MAX, TITLE_MAX
from ticketing.exceptions import ValidationError
from ticketing.models import Category, Priority, Status

VALID = {
    "title": "VPN down",
    "description": "Cannot connect",
    "category": "Network",
    "priority": "High",
    "creator": "bob",
}


def _count(db_path) -> int:
    with sqlite3.connect(db_path) as c:
        return c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]


@pytest.mark.req("FR-001", "FR-004", "AC-001")
def test_create_ticket_happy_path_ac001(db_path):
    t = service.create_ticket(db_path, **VALID)
    assert t.id >= 1
    assert t.status is Status.OPEN
    assert t.created_at and t.updated_at and t.created_at == t.updated_at
    assert t.resolution_note is None
    assert t.category is Category.NETWORK and t.priority is Priority.HIGH
    assert service.get_ticket(db_path, t.id) == t


@pytest.mark.req("FR-004", "AC-006")
def test_create_two_tickets_unique_ids_ac006(make_ticket):
    assert make_ticket().id != make_ticket().id


@pytest.mark.req("FR-001", "AC-001")
def test_create_accepts_enum_members(db_path):
    t = service.create_ticket(
        db_path, "t", "d", Category.ACCESS, Priority.CRITICAL, "carol"
    )
    assert t.category is Category.ACCESS and t.priority is Priority.CRITICAL


@pytest.mark.req("FR-003", "NFR-002", "AC-002")
@pytest.mark.parametrize("field", ["title", "description", "creator"])
@pytest.mark.parametrize("bad", ["", "   ", "\t\n  "])
def test_create_blank_required_text_ac002(db_path, field, bad):
    args = {**VALID, field: bad}
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(db_path, **args)
    assert ei.value.field == field
    assert ei.value.message
    assert _count(db_path) == 0


@pytest.mark.req("FR-003", "AC-002")
@pytest.mark.parametrize("field", ["title", "description", "creator", "category", "priority"])
def test_create_none_required_field_ac002(db_path, field):
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(db_path, **{**VALID, field: None})
    assert ei.value.field == field
    assert _count(db_path) == 0


@pytest.mark.req("FR-003", "AC-002")
@pytest.mark.parametrize("field", ["category", "priority"])
def test_create_blank_category_priority_ac002(db_path, field):
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(db_path, **{**VALID, field: "  "})
    assert ei.value.field == field


@pytest.mark.req("FR-003", "AC-003")
@pytest.mark.parametrize(
    ("field", "limit"),
    [("title", TITLE_MAX), ("description", DESCRIPTION_MAX), ("creator", CREATOR_MAX)],
)
def test_create_length_boundaries_ac003(db_path, field, limit):
    ok = service.create_ticket(db_path, **{**VALID, field: "x" * limit})
    assert len(getattr(ok, field)) == limit
    before = _count(db_path)
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(db_path, **{**VALID, field: "x" * (limit + 1)})
    assert ei.value.field == field
    assert _count(db_path) == before


@pytest.mark.req("FR-003", "AC-003")
def test_create_length_counted_after_trim_ac003(db_path):
    t = service.create_ticket(db_path, **{**VALID, "title": "  " + "x" * TITLE_MAX + "  "})
    assert t.title == "x" * TITLE_MAX


@pytest.mark.req("FR-003", "AC-002")
def test_create_trims_whitespace(db_path):
    t = service.create_ticket(db_path, **{**VALID, "title": "  hi  ", "creator": " bob "})
    assert t.title == "hi" and t.creator == "bob"


@pytest.mark.req("FR-003", "NFR-002")
@pytest.mark.parametrize("ch", ["\x00", "\x01", "\x1b", "\x7f", "\x08"])
@pytest.mark.parametrize("field", ["title", "description", "creator"])
def test_create_control_characters_rejected(db_path, field, ch):
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(db_path, **{**VALID, field: f"ab{ch}cd"})
    assert ei.value.field == field
    assert _count(db_path) == 0


@pytest.mark.req("FR-003")
def test_create_allows_newline_tab_in_description(db_path):
    t = service.create_ticket(db_path, **{**VALID, "description": "line1\nline2\tx"})
    assert t.description == "line1\nline2\tx"


@pytest.mark.req("FR-003")
@pytest.mark.parametrize("field", ["title", "description", "creator"])
@pytest.mark.parametrize("bad", [123, 1.5, ["a"], {"a": 1}, b"abc"])
def test_create_non_string_text_rejected(db_path, field, bad):
    with pytest.raises(ValidationError):
        service.create_ticket(db_path, **{**VALID, field: bad})


@pytest.mark.req("FR-002", "NFR-004", "AC-005")
@pytest.mark.parametrize("bad", ["Urgent", "low", "HIGH", "", "5", 3, "Medium; DROP"])
def test_create_invalid_priority_ac005(db_path, bad):
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(db_path, **{**VALID, "priority": bad})
    assert ei.value.field == "priority"
    assert _count(db_path) == 0


@pytest.mark.req("FR-003")
@pytest.mark.parametrize("bad", ["Printers", "hardware", "", 7, "Other "[:0]])
def test_create_invalid_category(db_path, bad):
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(db_path, **{**VALID, "category": bad})
    assert ei.value.field == "category"
    assert _count(db_path) == 0


@pytest.mark.req("FR-002", "AC-004")
@pytest.mark.parametrize("p", list(Priority))
def test_create_each_priority_stored_ac004(db_path, p):
    assert service.create_ticket(db_path, **{**VALID, "priority": p.value}).priority is p


@pytest.mark.req("FR-003")
@pytest.mark.parametrize("c", list(Category))
def test_create_each_category_stored(db_path, c):
    assert service.create_ticket(db_path, **{**VALID, "category": c.value}).category is c


@pytest.mark.req("FR-002", "AC-004")
def test_create_priority_is_required_no_default_in_service(db_path):
    """Service signature requires priority (UI supplies the Medium default)."""
    with pytest.raises(TypeError):
        service.create_ticket(  # type: ignore[call-arg]
            db_path, "t", "d", "Network", creator="x"
        )


@pytest.mark.req("FR-001", "FR-003", "NFR-002")
def test_create_unicode_roundtrip(db_path):
    t = service.create_ticket(db_path, **{**VALID, "title": "Drucker kaputt \u00fc \u4e2d\u6587"})
    assert service.get_ticket(db_path, t.id).title == "Drucker kaputt \u00fc \u4e2d\u6587"
