"""Updates, transitions, resolution notes (FR-008..011, FR-021, AC-008, AC-013..015, AC-030)."""

import itertools
import sqlite3
import time

import pytest

from ticketing import service
from ticketing.config import RESOLUTION_NOTE_MAX
from ticketing.exceptions import InvalidTransitionError, ValidationError
from ticketing.models import ALLOWED_TRANSITIONS, Priority, Status


def _row(db_path, tid):
    with sqlite3.connect(db_path) as c:
        return c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()


def _to_status(db_path, tid, target: Status) -> None:
    """Walk a fresh Open ticket to ``target`` along legal transitions."""
    path = {
        Status.OPEN: [],
        Status.IN_PROGRESS: [("In Progress", None)],
        Status.RESOLVED: [("Resolved", "done")],
        Status.CLOSED: [("Resolved", "done"), ("Closed", None)],
    }[target]
    for s, n in path:
        service.update_status(db_path, tid, s, n)


@pytest.mark.req("FR-008", "FR-011", "AC-013", "AC-008")
def test_update_status_changes_status_and_updated_at_ac013(db_path, make_ticket):
    t = make_ticket()
    time.sleep(1.1)
    u = service.update_status(db_path, t.id, Status.IN_PROGRESS)
    assert u.status is Status.IN_PROGRESS
    assert u.updated_at > t.updated_at
    assert u.created_at == t.created_at
    assert service.get_ticket(db_path, t.id).status is Status.IN_PROGRESS


@pytest.mark.req("FR-009", "FR-011", "AC-015")
def test_update_priority_ac015(db_path, make_ticket):
    t = make_ticket(priority="Low")
    time.sleep(1.1)
    u = service.update_priority(db_path, t.id, "Critical")
    assert u.priority is Priority.CRITICAL
    assert u.updated_at > t.updated_at
    assert u.status is Status.OPEN and u.title == t.title


@pytest.mark.req("FR-009", "AC-015")
@pytest.mark.parametrize("bad", ["Urgent", "", None, 3, "low"])
def test_update_priority_invalid_unchanged_ac015(db_path, make_ticket, bad):
    t = make_ticket()
    before = _row(db_path, t.id)
    with pytest.raises(ValidationError) as ei:
        service.update_priority(db_path, t.id, bad)
    assert ei.value.field == "priority"
    assert _row(db_path, t.id) == before


@pytest.mark.req("FR-021", "FR-011", "AC-030")
def test_update_resolution_note_ac030(db_path, make_ticket):
    t = make_ticket()
    time.sleep(1.1)
    u = service.update_resolution_note(db_path, t.id, "  Rebooted router  ")
    assert u.resolution_note == "Rebooted router"
    assert u.updated_at > t.updated_at
    assert u.status is Status.OPEN
    assert service.get_ticket(db_path, t.id).resolution_note == "Rebooted router"
    u2 = service.update_resolution_note(db_path, t.id, "Replaced cable")
    assert u2.resolution_note == "Replaced cable"


@pytest.mark.req("FR-021", "AC-030")
def test_resolution_note_length_boundary_ac030(db_path, make_ticket):
    t = make_ticket()
    ok = service.update_resolution_note(db_path, t.id, "n" * RESOLUTION_NOTE_MAX)
    assert len(ok.resolution_note) == RESOLUTION_NOTE_MAX
    before = _row(db_path, t.id)
    with pytest.raises(ValidationError) as ei:
        service.update_resolution_note(db_path, t.id, "n" * (RESOLUTION_NOTE_MAX + 1))
    assert ei.value.field == "resolution_note"
    assert _row(db_path, t.id) == before


@pytest.mark.req("FR-021", "AC-030")
@pytest.mark.parametrize("bad", ["", "   ", None, 5, "a\x00b"])
def test_resolution_note_invalid_unchanged(db_path, make_ticket, bad):
    t = make_ticket()
    before = _row(db_path, t.id)
    with pytest.raises(ValidationError):
        service.update_resolution_note(db_path, t.id, bad)
    assert _row(db_path, t.id) == before


@pytest.mark.req("FR-010", "AC-014")
@pytest.mark.parametrize("bad", ["Done", "open", "", None, 1, "Pending", "Closed; --"])
def test_update_status_invalid_value_unchanged_ac014(db_path, make_ticket, bad):
    t = make_ticket()
    before = _row(db_path, t.id)
    with pytest.raises(ValidationError) as ei:
        service.update_status(db_path, t.id, bad)
    assert ei.value.field == "status"
    assert _row(db_path, t.id) == before


@pytest.mark.req("FR-010", "AC-014", "AC-013")
@pytest.mark.parametrize(("cur", "new"), list(itertools.product(Status, Status)))
def test_transition_table_every_cell_ac013_ac014(db_path, make_ticket, cur, new):
    t = make_ticket()
    _to_status(db_path, t.id, cur)
    before = _row(db_path, t.id)
    allowed = new in ALLOWED_TRANSITIONS[cur]
    if allowed:
        u = service.update_status(db_path, t.id, new, "note for resolve")
        assert u.status is new
    else:
        with pytest.raises(InvalidTransitionError) as ei:
            service.update_status(db_path, t.id, new, "note")
        assert ei.value.current is cur and ei.value.requested is new
        assert _row(db_path, t.id) == before


@pytest.mark.req("FR-010")
def test_transition_table_matches_design():
    assert ALLOWED_TRANSITIONS == {
        Status.OPEN: {Status.IN_PROGRESS, Status.RESOLVED},
        Status.IN_PROGRESS: {Status.RESOLVED},
        Status.RESOLVED: {Status.IN_PROGRESS, Status.CLOSED},
        Status.CLOSED: set(),
    }


@pytest.mark.req("FR-010", "AC-014")
def test_closed_is_final_no_status_change_possible(db_path, make_ticket):
    t = make_ticket()
    _to_status(db_path, t.id, Status.CLOSED)
    for s in Status:
        with pytest.raises(InvalidTransitionError):
            service.update_status(db_path, t.id, s, "n")
    assert service.allowed_next_statuses(Status.CLOSED) == []


@pytest.mark.req("FR-010", "AC-014")
def test_same_status_rejected(db_path, make_ticket):
    t = make_ticket()
    with pytest.raises(InvalidTransitionError):
        service.update_status(db_path, t.id, Status.OPEN)


@pytest.mark.req("FR-010", "AC-014")
def test_closed_ticket_note_and_priority_still_editable(db_path, make_ticket):
    """Closed is final for status only (service behaviour); documented observation."""
    t = make_ticket()
    _to_status(db_path, t.id, Status.CLOSED)
    assert service.update_priority(db_path, t.id, "Low").priority is Priority.LOW
    assert service.update_resolution_note(db_path, t.id, "edit").resolution_note == "edit"


@pytest.mark.req("FR-021", "AC-030")
def test_resolved_requires_note_ac030(db_path, make_ticket):
    t = make_ticket()
    before = _row(db_path, t.id)
    for note in (None, "", "   "):
        with pytest.raises(ValidationError) as ei:
            service.update_status(db_path, t.id, Status.RESOLVED, note)
        assert ei.value.field == "resolution_note"
        assert _row(db_path, t.id) == before


@pytest.mark.req("FR-021", "AC-030")
def test_resolved_uses_note_passed_in_and_stores_it(db_path, make_ticket):
    t = make_ticket()
    u = service.update_status(db_path, t.id, Status.RESOLVED, " fixed it ")
    assert u.status is Status.RESOLVED and u.resolution_note == "fixed it"


@pytest.mark.req("FR-021", "AC-030")
def test_resolved_uses_previously_stored_note(db_path, make_ticket):
    t = make_ticket()
    service.update_resolution_note(db_path, t.id, "earlier note")
    u = service.update_status(db_path, t.id, Status.RESOLVED)
    assert u.status is Status.RESOLVED and u.resolution_note == "earlier note"


@pytest.mark.req("FR-021", "AC-030")
def test_reopen_keeps_note_and_closed_keeps_note(db_path, make_ticket):
    t = make_ticket()
    service.update_status(db_path, t.id, "Resolved", "n1")
    assert service.update_status(db_path, t.id, "In Progress").resolution_note == "n1"
    service.update_status(db_path, t.id, "Resolved")
    assert service.update_status(db_path, t.id, "Closed").resolution_note == "n1"


@pytest.mark.req("FR-021", "AC-030")
def test_status_update_with_overlong_note_rejected_unchanged(db_path, make_ticket):
    t = make_ticket()
    before = _row(db_path, t.id)
    with pytest.raises(ValidationError):
        service.update_status(db_path, t.id, "In Progress", "x" * (RESOLUTION_NOTE_MAX + 1))
    assert _row(db_path, t.id) == before


@pytest.mark.req("FR-021", "AC-030")
def test_status_update_with_note_on_non_resolved_stores_note(db_path, make_ticket):
    t = make_ticket()
    u = service.update_status(db_path, t.id, "In Progress", "looking into it")
    assert u.resolution_note == "looking into it"


@pytest.mark.req("FR-011", "AC-008")
def test_updated_at_never_before_created_at(db_path, make_ticket):
    t = make_ticket()
    u = service.update_priority(db_path, t.id, "High")
    assert u.updated_at >= u.created_at


@pytest.mark.req("FR-011", "AC-008")
def test_timestamp_format_utc_iso(make_ticket):
    t = make_ticket()
    import re

    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", t.created_at)


@pytest.mark.req("FR-008", "FR-010")
def test_allowed_next_statuses_helper():
    assert service.allowed_next_statuses(Status.OPEN) == [Status.IN_PROGRESS, Status.RESOLVED]
    assert service.allowed_next_statuses("Resolved") == [Status.IN_PROGRESS, Status.CLOSED]
    assert service.allowed_next_statuses(Status.IN_PROGRESS) == [Status.RESOLVED]
    with pytest.raises(ValidationError):
        service.allowed_next_statuses("Nope")
