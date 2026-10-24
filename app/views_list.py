"""Ticket listing with search and filters (FR-006)."""

from __future__ import annotations

import streamlit as st

from app import common
from ticketing import service
from ticketing.config import SEARCH_MAX
from ticketing.models import Category, Priority, Status, TicketFilter


def _label(option: object) -> str:
    """Display label for a filter option (the ALL sentinel or an enum)."""
    if isinstance(option, str) and option == common.ALL:
        return option
    return str(option.value)  # type: ignore[attr-defined]


def filter_controls(key: str) -> TicketFilter:
    """Render search + status/priority/category controls and return a TicketFilter."""
    c0, c1, c2, c3 = st.columns([2, 1, 1, 1])
    search = c0.text_input(
        "Search title/description", key=f"{key}_search", max_chars=SEARCH_MAX
    ).strip()
    status = c1.selectbox(
        "Status", [common.ALL, *Status], key=f"{key}_status", format_func=_label
    )
    priority = c2.selectbox(
        "Priority", [common.ALL, *Priority], key=f"{key}_priority", format_func=_label
    )
    category = c3.selectbox(
        "Category", [common.ALL, *Category], key=f"{key}_category", format_func=_label
    )
    return TicketFilter(
        status=None if status == common.ALL else status,
        priority=None if priority == common.ALL else priority,
        category=None if category == common.ALL else category,
        search=search or None,
    )


def render_all(db_path: common.Path) -> None:
    """All-tickets table for engineers (FR-006)."""
    if st.button("Refresh", key="refresh_all"):
        st.rerun()
    flt = filter_controls("all")
    ok, tickets = common.call(service.list_tickets, db_path, flt)
    if ok:
        common.show_tickets(tickets, "No tickets match the selected filters.")
