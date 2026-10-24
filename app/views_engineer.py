"""Support Engineer views: all tickets and ticket detail/update (FR-006..011, FR-021)."""

from __future__ import annotations

import streamlit as st

from app import common
from app.views_list import render_all
from ticketing import service
from ticketing.config import RESOLUTION_NOTE_MAX
from ticketing.models import Priority, Ticket


def render(db_path: common.Path) -> None:
    """Render the engineer tabs."""
    tab_all, tab_detail = st.tabs(["All tickets", "Ticket detail"])
    with tab_all:
        render_all(db_path)
    with tab_detail:
        _detail(db_path)


def _detail(db_path: common.Path) -> None:
    """Select a ticket and show update forms."""
    common.show_flash()
    ok, tickets = common.call(service.list_tickets, db_path)
    if not ok:
        return
    if not tickets:
        st.info("There are no tickets yet.")
        return
    by_id = {t.id: t for t in tickets}
    ticket_id = st.selectbox(
        "Ticket", list(by_id), key="selected_ticket_id",
        format_func=lambda i: common.plain(
            f"#{i} - {by_id[i].title} [{by_id[i].status.value}]"
        ),
    )
    ok, ticket = common.call(service.get_ticket, db_path, ticket_id)
    if not ok:
        return
    _show_details(ticket)
    _status_form(db_path, ticket)
    _priority_form(db_path, ticket)
    _note_form(db_path, ticket)


def _show_details(t: Ticket) -> None:
    """Render ticket fields as plain text (no HTML)."""
    st.subheader(f"Ticket #{t.id}")
    st.text(f"Title: {t.title}")
    st.text(f"Creator: {t.creator}")
    st.text(
        f"Category: {t.category.value}   Priority: {t.priority.value}   "
        f"Status: {t.status.value}"
    )
    st.text(f"Created (UTC): {t.created_at}   Updated (UTC): {t.updated_at}")
    st.text("Description:")
    st.text(t.description)
    st.text("Resolution note:")
    st.text(t.resolution_note or "(none)")


def _status_form(db_path: common.Path, t: Ticket) -> None:
    """Change status using only allowed next statuses (FR-008, FR-010, D-04)."""
    st.markdown("**Change status**")
    ok, options = common.call(service.allowed_next_statuses, t.status)
    if not ok:
        return
    if not options:
        st.info(f"Status is {t.status.value}; no further changes are allowed.")
        return
    with st.form(f"status_{t.id}"):
        new_status = st.selectbox("New status", options, format_func=lambda s: s.value)
        note = st.text_area(
            "Resolution note (required when moving to Resolved)",
            value=t.resolution_note or "", max_chars=RESOLUTION_NOTE_MAX,
        )
        go = st.form_submit_button("Update status")
    if go:
        ok, upd = common.call(service.update_status, db_path, t.id, new_status, note or None)
        if ok:
            common.flash(f"Ticket #{upd.id} status changed to {upd.status.value}.")
            st.rerun()


def _priority_form(db_path: common.Path, t: Ticket) -> None:
    """Change priority (FR-009)."""
    st.markdown("**Change priority**")
    with st.form(f"prio_{t.id}"):
        new_p = st.selectbox("Priority", list(Priority), index=list(Priority).index(t.priority),
                             format_func=lambda p: p.value)
        go = st.form_submit_button("Update priority")
    if go:
        ok, upd = common.call(service.update_priority, db_path, t.id, new_p)
        if ok:
            common.flash(f"Ticket #{upd.id} priority set to {upd.priority.value}.")
            st.rerun()


def _note_form(db_path: common.Path, t: Ticket) -> None:
    """Add or edit the resolution note in any status (FR-021)."""
    st.markdown("**Resolution note**")
    with st.form(f"note_{t.id}"):
        note = st.text_area("Note", value=t.resolution_note or "", max_chars=RESOLUTION_NOTE_MAX)
        go = st.form_submit_button("Save note")
    if go:
        ok, upd = common.call(service.update_resolution_note, db_path, t.id, note)
        if ok:
            common.flash(f"Resolution note saved for ticket #{upd.id}.")
            st.rerun()

