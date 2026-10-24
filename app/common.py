"""Shared UI helpers: DB bootstrap, DEMO banner, flash messages, ticket tables (FR-018, NFR-002)."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import streamlit as st

from ticketing.config import get_db_path
from ticketing.exceptions import TicketingError
from ticketing.models import Ticket
from ticketing.service import init_database

DEMO_BANNER = (
    "DEMO MODE: the role selector is not login or security. Anyone can choose any role "
    "and view or change any ticket. Do not enter confidential information."
)
SIDEBAR_CAPTION = "Demo role selector, not authentication."
ALL = "All"


@st.cache_resource
def _init_db(path_str: str) -> str:
    """Initialise the schema once per process (FR-017); returns the path string."""
    init_database(path_str)
    return path_str


def get_path() -> Path:
    """Return the DB path after ensuring the schema exists (cached init)."""
    path = get_db_path()
    _init_db(str(path))
    return path


def demo_banner() -> None:
    """Render the persistent DEMO banner (FR-018, NFR-009, AC-023)."""
    st.warning(DEMO_BANNER)


def flash(message: str) -> None:
    """Store a one-shot success message shown on the next run."""
    st.session_state["flash"] = message


def show_flash() -> None:
    """Display and clear a pending one-shot success message."""
    msg = st.session_state.pop("flash", None)
    if msg:
        st.success(msg)


def plain(text: str) -> str:
    """Escape Markdown/HTML-significant characters so user text renders as plain text."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|>~$<&:])", r"\\\1", text)


def call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[bool, Any]:
    """Run a service call; show ``st.error`` for expected errors, never a traceback.

    Returns ``(ok, result)``.
    """
    try:
        return True, fn(*args, **kwargs)
    except TicketingError as exc:
        st.error(plain(exc.message) if exc.message else "The request could not be completed.")
    except NotImplementedError:
        st.error("This feature is not available yet.")
    return False, None


def ticket_rows(tickets: Sequence[Ticket]) -> list[dict[str, Any]]:
    """Convert tickets to plain table rows (timestamps are UTC)."""
    return [
        {
            "ID": t.id,
            "Title": t.title,
            "Category": t.category.value,
            "Priority": t.priority.value,
            "Status": t.status.value,
            "Creator": t.creator,
            "Created (UTC)": t.created_at,
            "Updated (UTC)": t.updated_at,
            "Resolution note": t.resolution_note or "",
        }
        for t in tickets
    ]


def show_tickets(tickets: Sequence[Ticket], empty_msg: str = "No tickets found.") -> None:
    """Render a ticket table as plain text, or an empty-state message (AC-009)."""
    if not tickets:
        st.info(empty_msg)
        return
    st.caption(f"{len(tickets)} ticket(s)")
    st.dataframe(ticket_rows(tickets), width="stretch", hide_index=True)
