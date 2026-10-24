"""Streamlit entry point: ``python -m streamlit run app/main.py`` (FR-018, NFR-009, NFR-010).

The role selector is a DEMO convenience only; it is NOT authentication or authorization.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st  # noqa: E402  (must follow sys.path bootstrap)

from app import common, views_employee, views_engineer, views_manager  # noqa: E402  (must follow sys.path bootstrap)
from ticketing.config import CREATOR_MAX  # noqa: E402  (must follow sys.path bootstrap)

logger = logging.getLogger(__name__)

LOOPBACK_ADDRESSES = frozenset({"127.0.0.1", "::1", "localhost"})
LAUNCH_HELP = (
    "This app has no authentication and must only run on 127.0.0.1. "
    "Launch it from the repository root with: "
    "`python -m streamlit run app/main.py --server.address 127.0.0.1`"
)


def is_loopback_address(addr: object) -> bool:
    """Return True only for an explicit loopback bind address (unset/empty = all interfaces)."""
    if not isinstance(addr, str):
        return False
    return addr.strip().strip("[]").lower() in LOOPBACK_ADDRESSES


ROLES = ("Employee", "Support Engineer", "Manager")


def main() -> None:
    """Render sidebar, DEMO banner and the selected role's view."""
    st.set_page_config(page_title="IT Support Tickets (DEMO)", layout="wide")
    st.title("IT Support Ticket Management")
    bind = st.get_option("server.address")
    if not is_loopback_address(bind):
        st.error(f"Refusing to start: server bind address is not loopback. {LAUNCH_HELP}")
        st.stop()
    with st.sidebar:
        st.header("Demo role")
        role = st.selectbox("Role", ROLES, key="role")
        st.caption(common.SIDEBAR_CAPTION)
        name = ""
        if role == "Employee":
            name = st.text_input("Your name", key="requester_name", max_chars=CREATOR_MAX)
    common.demo_banner()
    try:
        db_path = common.get_path()
    except Exception as exc:  # noqa: BLE001 - show a safe message, never a traceback
        from ticketing.exceptions import TicketingError

        logger.error("Database bootstrap failed: %s", type(exc).__name__, exc_info=True)
        msg = (
            common.plain(exc.message)
            if isinstance(exc, TicketingError)
            else "The database could not be opened."
        )
        st.error(msg)
        return
    if role == "Employee":
        views_employee.render(db_path, name)
    elif role == "Support Engineer":
        views_engineer.render(db_path)
    else:
        views_manager.render(db_path)


main()
