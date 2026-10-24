"""Streamlit AppTest smoke tests for the three DEMO roles (FR-018, FR-022, AC-022, AC-031)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.common import DEMO_BANNER
from ticketing import service

MAIN = str(Path(__file__).resolve().parent.parent / "app" / "main.py")

pytestmark = pytest.mark.ui


def _app(db_path) -> AppTest:
    at = AppTest.from_file(MAIN, default_timeout=30)
    at.run()
    return at


def _select_role(at: AppTest, role: str) -> AppTest:
    at.sidebar.selectbox(key="role").select(role)
    return at.run()


def _texts(elements) -> str:
    return "\n".join(str(e.value) for e in elements)


@pytest.fixture
def at(db_path, monkeypatch) -> AppTest:
    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    return _app(db_path)


@pytest.mark.req("FR-022", "AC-031", "NFR-009")
@pytest.mark.parametrize("role", ["Employee", "Support Engineer", "Manager"])
def test_demo_banner_visible_for_every_role_ac031(at, role):
    _select_role(at, role)
    assert not at.exception
    assert any(DEMO_BANNER == w.value for w in at.warning)
    assert "DEMO" in DEMO_BANNER and "not login or security" in DEMO_BANNER


@pytest.mark.req("FR-018", "AC-022")
def test_role_selector_offers_three_roles_ac022(at):
    assert list(at.sidebar.selectbox(key="role").options) == [
        "Employee", "Support Engineer", "Manager",
    ]
    assert not at.exception


@pytest.mark.req("FR-001", "FR-004", "AC-001", "AC-022", "NFR-001", "AC-028")
def test_employee_create_ticket_flow_ac001(at, db_path):
    _select_role(at, "Employee")
    assert [t.label for t in at.tabs] == ["New ticket", "My tickets"]
    at.sidebar.text_input(key="requester_name").input("Dana").run()
    at.text_input(key="nt_title_0").input("Laptop will not boot")
    at.text_area(key="nt_desc_0").input("Black screen after logo")
    at.selectbox(key="nt_cat_0").select_index(0)
    at.button[[b.label for b in at.button].index("Submit ticket")].click().run()
    assert not at.exception
    tickets = service.list_tickets_for_creator(db_path, "Dana")
    assert len(tickets) == 1
    assert tickets[0].title == "Laptop will not boot"
    assert tickets[0].status.value == "Open"
    assert any("Ticket #" in s.value and "created" in s.value for s in at.success)


@pytest.mark.req("FR-003", "NFR-002", "AC-002")
def test_employee_blank_title_shows_error_ac002(at, db_path):
    _select_role(at, "Employee")
    at.sidebar.text_input(key="requester_name").input("Dana").run()
    at.text_area(key="nt_desc_0").input("something")
    at.button[[b.label for b in at.button].index("Submit ticket")].click().run()
    assert not at.exception
    assert any("Title is required" in e.value for e in at.error)
    assert service.list_tickets(db_path) == []


@pytest.mark.req("FR-003", "AC-002")
def test_employee_missing_name_shows_error(at, db_path):
    _select_role(at, "Employee")
    at.text_input(key="nt_title_0").input("T")
    at.text_area(key="nt_desc_0").input("D")
    at.button[[b.label for b in at.button].index("Submit ticket")].click().run()
    assert any("name is required" in e.value.lower() for e in at.error)
    assert service.list_tickets(db_path) == []


@pytest.mark.req("FR-005", "FR-021", "AC-007", "AC-030")
def test_employee_sees_own_tickets_and_note_ac007(db_path, monkeypatch):
    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    mine = service.create_ticket(db_path, "Mine", "d", "Other", "Low", "Dana")
    service.create_ticket(db_path, "Theirs", "d", "Other", "Low", "Evan")
    service.update_status(db_path, mine.id, "Resolved", "NOTE-VISIBLE")
    at = _app(db_path)
    _select_role(at, "Employee")
    at.sidebar.text_input(key="requester_name").input("dana").run()
    assert not at.exception
    rows = [r for df in at.dataframe for r in df.value.to_dict("records")]
    assert [r["Title"] for r in rows] == ["Mine"]
    assert rows[0]["Resolution note"] == "NOTE-VISIBLE"
    assert rows[0]["Status"] == "Resolved"


@pytest.mark.req("FR-006", "FR-007", "FR-008", "FR-009", "FR-021", "AC-009", "AC-013", "AC-015")
def test_engineer_view_and_updates_ac013_ac015(db_path, monkeypatch):
    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    t = service.create_ticket(db_path, "Wifi", "drops", "Network", "Low", "Dana")
    service.create_ticket(db_path, "Mouse", "dead", "Hardware", "High", "Evan")
    at = _app(db_path)
    _select_role(at, "Support Engineer")
    assert not at.exception
    assert [x.label for x in at.tabs] == ["All tickets", "Ticket detail"]
    rows = [r for df in at.dataframe for r in df.value.to_dict("records")]
    assert len(rows) == 2

    at.selectbox(key="selected_ticket_id").select(t.id).run()
    labels = [b.label for b in at.button]
    # priority change
    prio_box = [s for s in at.selectbox if s.label == "Priority" and s.value == "Low"][0]
    prio_box.select("Critical")
    at.button[[b.label for b in at.button].index("Update priority")].click().run()
    assert not at.exception
    assert service.get_ticket(db_path, t.id).priority.value == "Critical"
    assert "Update status" in labels

    # status change to Resolved without note -> error, unchanged
    new_status = [s for s in at.selectbox if s.label == "New status"][0]
    new_status.select("Resolved")
    at.button[[b.label for b in at.button].index("Update status")].click().run()
    assert any("resolution note is required" in e.value.lower() for e in at.error)
    assert service.get_ticket(db_path, t.id).status.value == "Open"

    # now with a note
    note_area = [a for a in at.text_area if a.label.startswith("Resolution note (required")][0]
    note_area.input("Replaced AP")
    at.button[[b.label for b in at.button].index("Update status")].click().run()
    assert not at.exception
    got = service.get_ticket(db_path, t.id)
    assert got.status.value == "Resolved" and got.resolution_note == "Replaced AP"


@pytest.mark.req("FR-010", "AC-014")
def test_engineer_closed_ticket_offers_no_status_change(db_path, monkeypatch):
    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    t = service.create_ticket(db_path, "Old", "d", "Other", "Low", "Dana")
    service.update_status(db_path, t.id, "Resolved", "n")
    service.update_status(db_path, t.id, "Closed")
    at = _app(db_path)
    _select_role(at, "Support Engineer")
    assert not at.exception
    assert "Update status" not in [b.label for b in at.button]
    assert any("no further changes" in i.value for i in at.info)


@pytest.mark.req("FR-006", "AC-010")
def test_engineer_filter_no_match_shows_empty_state_ac010(db_path, monkeypatch):
    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    service.create_ticket(db_path, "Wifi", "drops", "Network", "Low", "Dana")
    at = _app(db_path)
    _select_role(at, "Support Engineer")
    at.selectbox(key="all_priority").select_index(4).run()  # Critical
    assert not at.exception
    assert any("No tickets match" in i.value for i in at.info)


@pytest.mark.req("FR-012", "FR-013", "FR-014", "FR-015", "FR-020", "AC-016", "AC-022")
def test_manager_dashboard_empty_ac016(at):
    _select_role(at, "Manager")
    assert not at.exception
    assert {m.label: m.value for m in at.metric} == {
        "Total": "0", "Open": "0", "In Progress": "0", "Resolved": "0", "Closed": "0",
    }
    assert any("No tickets yet" in i.value for i in at.info)


@pytest.mark.req("FR-012", "FR-013", "FR-014", "FR-015", "FR-020", "FR-016", "AC-017", "AC-020")
def test_manager_dashboard_counts_ac017(db_path, monkeypatch):
    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    a = service.create_ticket(db_path, "a", "d", "Network", "High", "x")
    service.create_ticket(db_path, "b", "d", "Other", "Low", "x")
    service.update_status(db_path, a.id, "In Progress")
    at = _app(db_path)
    _select_role(at, "Manager")
    assert not at.exception
    assert {m.label: m.value for m in at.metric} == {
        "Total": "2", "Open": "1", "In Progress": "1", "Resolved": "0", "Closed": "0",
    }
    assert len(at.table) == 2
