"""Retrieval, listing, filters (FR-005..007, AC-007..012, AC-010)."""

import pytest

from ticketing import service
from ticketing.exceptions import TicketNotFoundError, ValidationError
from ticketing.models import Category, Priority, Status, TicketFilter


@pytest.mark.req("FR-007", "AC-011")
def test_get_ticket_returns_all_fields_ac011(make_ticket, db_path):
    t = make_ticket()
    got = service.get_ticket(db_path, t.id)
    for attr in (
        "id title description category priority status creator created_at updated_at "
        "resolution_note"
    ).split():
        assert hasattr(got, attr)
    assert got.resolution_note is None


@pytest.mark.req("FR-007", "AC-012")
def test_get_unknown_id_not_found_ac012(db_path):
    with pytest.raises(TicketNotFoundError) as ei:
        service.get_ticket(db_path, 9999)
    assert ei.value.ticket_id == 9999


@pytest.mark.req("FR-007", "AC-012")
@pytest.mark.parametrize("bad", [0, -1, -100, "1", 1.0, None, True, False, [1], "abc"])
def test_get_invalid_id_validation_error(db_path, make_ticket, bad):
    make_ticket()
    with pytest.raises(ValidationError) as ei:
        service.get_ticket(db_path, bad)
    assert ei.value.field == "ticket_id"


@pytest.mark.req("FR-007", "AC-012")
@pytest.mark.parametrize(
    "call",
    [
        lambda p, i: service.update_status(p, i, "In Progress"),
        lambda p, i: service.update_priority(p, i, "High"),
        lambda p, i: service.update_resolution_note(p, i, "note"),
    ],
)
@pytest.mark.parametrize("bad", [0, -5, "1", None, 2.5])
def test_update_invalid_id_rejected(db_path, call, bad):
    with pytest.raises(ValidationError):
        call(db_path, bad)


@pytest.mark.req("FR-007", "AC-012")
def test_update_unknown_id_not_found(db_path):
    with pytest.raises(TicketNotFoundError):
        service.update_status(db_path, 42, "In Progress")
    with pytest.raises(TicketNotFoundError):
        service.update_priority(db_path, 42, "High")
    with pytest.raises(TicketNotFoundError):
        service.update_resolution_note(db_path, 42, "n")


@pytest.mark.req("FR-006", "AC-009")
def test_list_empty_and_all_ac009(db_path, make_ticket):
    assert service.list_tickets(db_path) == []
    for i in range(5):
        make_ticket(title=f"t{i}")
    assert len(service.list_tickets(db_path)) == 5
    assert len(service.list_tickets(db_path, TicketFilter())) == 5


@pytest.mark.req("FR-006", "AC-009")
def test_list_newest_first(db_path, make_ticket):
    a, b, c = make_ticket(title="a"), make_ticket(title="b"), make_ticket(title="c")
    ids = [t.id for t in service.list_tickets(db_path)]
    assert ids == [c.id, b.id, a.id]


@pytest.mark.req("FR-005", "AC-007")
def test_list_for_creator_only_own_ac007(db_path, make_ticket):
    x1, x2 = make_ticket(creator="X"), make_ticket(creator="X")
    make_ticket(creator="Y")
    got = service.list_tickets_for_creator(db_path, "X")
    assert {t.id for t in got} == {x1.id, x2.id}


@pytest.mark.req("FR-005", "AC-007")
def test_list_for_creator_case_insensitive_exact_and_trim(db_path, make_ticket):
    t = make_ticket(creator="Alice Smith")
    make_ticket(creator="Alice Smithson")
    make_ticket(creator="Alice")
    assert [x.id for x in service.list_tickets_for_creator(db_path, "alice smith")] == [t.id]
    assert [x.id for x in service.list_tickets_for_creator(db_path, "  ALICE SMITH ")] == [t.id]
    assert service.list_tickets_for_creator(db_path, "Smith") == []


@pytest.mark.req("FR-005", "AC-007")
def test_list_for_creator_wildcards_not_special(db_path, make_ticket):
    make_ticket(creator="bob")
    assert service.list_tickets_for_creator(db_path, "%") == []
    assert service.list_tickets_for_creator(db_path, "b_b") == []


@pytest.mark.req("FR-005", "AC-002")
@pytest.mark.parametrize("bad", ["", "  ", None])
def test_list_for_creator_blank_rejected(db_path, bad):
    with pytest.raises(ValidationError):
        service.list_tickets_for_creator(db_path, bad)


@pytest.mark.req("FR-005", "AC-007")
def test_list_for_creator_unknown_returns_empty(db_path, make_ticket):
    make_ticket()
    assert service.list_tickets_for_creator(db_path, "nobody") == []


@pytest.fixture
def mixed(db_path, make_ticket):
    t1 = make_ticket(title="Printer jam", description="paper stuck", priority="Low",
                     category="Hardware")
    t2 = make_ticket(title="VPN", description="100% loss", priority="High", category="Network")
    t3 = make_ticket(title="Snake_case bug", description="app crash", priority="High",
                     category="Software")
    service.update_status(db_path, t2.id, "In Progress")
    service.update_status(db_path, t3.id, "Resolved", "fixed")
    return t1, t2, t3


@pytest.mark.req("FR-006", "AC-010")
def test_filter_by_status_ac010(db_path, mixed):
    got = service.list_tickets(db_path, TicketFilter(status=Status.IN_PROGRESS))
    assert [t.id for t in got] == [mixed[1].id]


@pytest.mark.req("FR-006", "AC-010")
def test_filter_by_priority_ac010(db_path, mixed):
    got = service.list_tickets(db_path, TicketFilter(priority=Priority.HIGH))
    assert {t.id for t in got} == {mixed[1].id, mixed[2].id}


@pytest.mark.req("FR-006", "AC-010")
def test_filter_by_category(db_path, mixed):
    got = service.list_tickets(db_path, TicketFilter(category=Category.SOFTWARE))
    assert [t.id for t in got] == [mixed[2].id]


@pytest.mark.req("FR-006", "AC-010")
def test_filter_accepts_string_values(db_path, mixed):
    got = service.list_tickets(db_path, TicketFilter(status="Open", priority="Low"))
    assert [t.id for t in got] == [mixed[0].id]


@pytest.mark.req("FR-006", "AC-010")
def test_filter_combined_ac010(db_path, mixed):
    f = TicketFilter(status=Status.RESOLVED, priority=Priority.HIGH, category=Category.SOFTWARE)
    assert [t.id for t in service.list_tickets(db_path, f)] == [mixed[2].id]
    f2 = TicketFilter(status=Status.OPEN, priority=Priority.HIGH)
    assert service.list_tickets(db_path, f2) == []


@pytest.mark.req("FR-006", "AC-010")
def test_filter_no_match_returns_empty_list_ac010(db_path, mixed):
    assert service.list_tickets(db_path, TicketFilter(status=Status.CLOSED)) == []


@pytest.mark.req("FR-006", "AC-010")
def test_filter_invalid_values_rejected(db_path):
    for f in (TicketFilter(status="Bogus"), TicketFilter(priority="Bogus"),
              TicketFilter(category="Bogus")):
        with pytest.raises(ValidationError):
            service.list_tickets(db_path, f)


@pytest.mark.req("FR-006")
def test_search_case_insensitive_title_and_description(db_path, mixed):
    assert [t.id for t in service.list_tickets(db_path, TicketFilter(search="PRINTER"))] == [
        mixed[0].id
    ]
    assert [t.id for t in service.list_tickets(db_path, TicketFilter(search="crash"))] == [
        mixed[2].id
    ]


@pytest.mark.req("FR-006", "AC-025")
def test_search_percent_literal(db_path, mixed):
    got = service.list_tickets(db_path, TicketFilter(search="%"))
    assert [t.id for t in got] == [mixed[1].id]
    assert [t.id for t in service.list_tickets(db_path, TicketFilter(search="100%"))] == [
        mixed[1].id
    ]


@pytest.mark.req("FR-006", "AC-025")
def test_search_underscore_literal(db_path, mixed):
    got = service.list_tickets(db_path, TicketFilter(search="_"))
    assert [t.id for t in got] == [mixed[2].id]
    assert service.list_tickets(db_path, TicketFilter(search="Snake_case"))[0].id == mixed[2].id
    assert service.list_tickets(db_path, TicketFilter(search="Snake-case")) == []


@pytest.mark.req("FR-006", "AC-025")
def test_search_backslash_literal(db_path, make_ticket):
    t = make_ticket(title=r"C:\temp path")
    make_ticket(title="other")
    assert [x.id for x in service.list_tickets(db_path, TicketFilter(search="\\"))] == [t.id]


@pytest.mark.req("FR-006")
def test_search_blank_means_no_filter_and_combines(db_path, mixed):
    assert len(service.list_tickets(db_path, TicketFilter(search="   "))) == 3
    f = TicketFilter(search="app", priority=Priority.HIGH)
    assert [t.id for t in service.list_tickets(db_path, f)] == [mixed[2].id]
    assert service.list_tickets(db_path, TicketFilter(search="app", priority=Priority.LOW)) == []


@pytest.mark.req("FR-006")
def test_search_non_string_rejected(db_path):
    with pytest.raises(ValidationError):
        service.list_tickets(db_path, TicketFilter(search=5))  # type: ignore[arg-type]
