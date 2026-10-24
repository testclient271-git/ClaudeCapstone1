"""Employee views: create ticket and My tickets (FR-001..005, AC-028)."""

from __future__ import annotations

import streamlit as st

from app import common
from app.views_list import filter_controls
from ticketing import service
from ticketing.config import DESCRIPTION_MAX, TITLE_MAX
from ticketing.models import Category, Priority


def render(db_path: common.Path, requester: str) -> None:
    """Render the Employee tabs for the given requester name."""
    tab_new, tab_mine = st.tabs(["New ticket", "My tickets"])
    with tab_new:
        _new_ticket(db_path, requester)
    with tab_mine:
        _my_tickets(db_path, requester)


def _new_ticket(db_path: common.Path, requester: str) -> None:
    """Ticket creation form (FR-001..004)."""
    common.show_flash()
    if requester:
        st.text(f"Creating as: {requester}")
    else:
        st.caption("Creating as: (enter your name in the sidebar)")
    n = st.session_state.get("form_n", 0)  # bumped on success to reset the form
    with st.form("new_ticket"):
        title = st.text_input("Title", max_chars=TITLE_MAX, key=f"nt_title_{n}")
        description = st.text_area("Description", max_chars=DESCRIPTION_MAX, key=f"nt_desc_{n}")
        category = st.selectbox(
            "Category", list(Category), format_func=lambda c: c.value, key=f"nt_cat_{n}"
        )
        priority = st.selectbox(
            "Priority", list(Priority), index=list(Priority).index(Priority.MEDIUM),
            format_func=lambda p: p.value, key=f"nt_prio_{n}",
        )
        submitted = st.form_submit_button("Submit ticket")
    if submitted:
        ok, ticket = common.call(
            service.create_ticket, db_path, title, description, category, priority, requester
        )
        if ok:
            st.session_state["form_n"] = n + 1
            common.flash(f"Ticket #{ticket.id} created with status {ticket.status.value}.")
            st.rerun()


def _my_tickets(db_path: common.Path, requester: str) -> None:
    """List the requester's own tickets with optional filters (FR-005, FR-006)."""
    if st.button("Refresh", key="refresh_mine"):
        st.rerun()
    if not requester.strip():
        st.info("Enter your name in the sidebar to see your tickets.")
        return
    ok, tickets = common.call(service.list_tickets_for_creator, db_path, requester)
    if not ok:
        return
    flt = filter_controls("mine")
    shown = [
        t for t in tickets
        if (flt.status is None or t.status == flt.status)
        and (flt.priority is None or t.priority == flt.priority)
        and (flt.category is None or t.category == flt.category)
        and (not flt.search
             or flt.search.lower() in t.title.lower()
             or flt.search.lower() in t.description.lower())
    ]
    common.show_tickets(shown, "You have no matching tickets.")
