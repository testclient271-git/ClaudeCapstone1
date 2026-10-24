"""Dashboard statistics (FR-012..016, FR-020, AC-016..020, AC-029)."""

import pytest

from ticketing import service
from ticketing.models import Category, Priority, Status


@pytest.mark.req("FR-012", "FR-015", "FR-020", "AC-016", "AC-019", "AC-029")
def test_dashboard_empty_db_zero_filled_ac016(db_path):
    s = service.get_dashboard_stats(db_path)
    assert (s.total, s.open, s.in_progress, s.resolved, s.closed) == (0, 0, 0, 0, 0)
    assert s.by_priority == {p: 0 for p in Priority}
    assert s.by_category == {c: 0 for c in Category}


@pytest.fixture
def populated(db_path, make_ticket):
    a = make_ticket(priority="Low", category="Hardware")
    b = make_ticket(priority="High", category="Network")
    c = make_ticket(priority="High", category="Network")
    d = make_ticket(priority="Critical", category="Other")
    e = make_ticket(priority="High", category="Software")
    service.update_status(db_path, b.id, "In Progress")
    service.update_status(db_path, c.id, "Resolved", "ok")
    service.update_status(db_path, d.id, "Resolved", "ok")
    service.update_status(db_path, d.id, "Closed")
    return a, b, c, d, e


@pytest.mark.req("FR-012", "FR-013", "FR-014", "AC-016", "AC-017", "AC-018")
def test_dashboard_status_counts_ac017_ac018(db_path, populated):
    s = service.get_dashboard_stats(db_path)
    assert s.total == 5
    assert (s.open, s.in_progress, s.resolved, s.closed) == (2, 1, 1, 1)
    assert s.open + s.in_progress + s.resolved + s.closed == s.total


@pytest.mark.req("FR-015", "AC-019")
def test_dashboard_by_priority_ac019(db_path, populated):
    s = service.get_dashboard_stats(db_path)
    assert s.by_priority == {
        Priority.LOW: 1, Priority.MEDIUM: 0, Priority.HIGH: 3, Priority.CRITICAL: 1,
    }
    assert list(s.by_priority) == list(Priority)
    assert sum(s.by_priority.values()) == s.total


@pytest.mark.req("FR-020", "AC-029")
def test_dashboard_by_category_ac029(db_path, populated):
    s = service.get_dashboard_stats(db_path)
    assert s.by_category[Category.NETWORK] == 2
    assert s.by_category[Category.ACCESS] == 0
    assert list(s.by_category) == list(Category)
    assert sum(s.by_category.values()) == s.total


@pytest.mark.req("FR-016", "AC-020")
def test_dashboard_reflects_changes_ac020(db_path, make_ticket):
    assert service.get_dashboard_stats(db_path).total == 0
    t = make_ticket(priority="Low")
    s = service.get_dashboard_stats(db_path)
    assert s.total == 1 and s.open == 1 and s.by_priority[Priority.LOW] == 1
    service.update_priority(db_path, t.id, "Critical")
    s = service.get_dashboard_stats(db_path)
    assert s.by_priority[Priority.LOW] == 0 and s.by_priority[Priority.CRITICAL] == 1
    service.update_status(db_path, t.id, "In Progress")
    s = service.get_dashboard_stats(db_path)
    assert s.open == 0 and s.in_progress == 1


@pytest.mark.req("FR-016", "AC-016")
def test_dashboard_sum_consistency_many(db_path, make_ticket):
    for i in range(30):
        make_ticket(priority=list(Priority)[i % 4].value, category=list(Category)[i % 5].value)
    s = service.get_dashboard_stats(db_path)
    assert s.total == 30
    assert sum(s.by_priority.values()) == 30 == sum(s.by_category.values())
    assert s.open == 30
    assert Status.OPEN.value == "Open"
