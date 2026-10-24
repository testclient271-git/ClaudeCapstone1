"""Manager dashboard (FR-012..016, FR-020)."""

from __future__ import annotations

import streamlit as st

from app import common
from ticketing import service


def render(db_path: common.Path) -> None:
    """Render metrics, breakdown tables and bar charts; data is re-read on each run (FR-016)."""
    if st.button("Refresh", key="refresh_dash"):
        st.rerun()
    ok, s = common.call(service.get_dashboard_stats, db_path)
    if not ok:
        return
    cols = st.columns(5)
    for col, (label, value) in zip(
        cols,
        [("Total", s.total), ("Open", s.open), ("In Progress", s.in_progress),
         ("Resolved", s.resolved), ("Closed", s.closed)],
        strict=True,
    ):
        col.metric(label, value)
    if s.total == 0:
        st.info("No tickets yet; all counts are zero.")
    left, right = st.columns(2)
    with left:
        st.subheader("Tickets by priority")
        rows = {
            "Priority": [p.value for p in s.by_priority],
            "Tickets": list(s.by_priority.values()),
        }
        st.bar_chart(
            rows, x="Priority", y="Tickets",
            x_label="Priority", y_label="Number of tickets",
        )
        st.table(rows)
    with right:
        st.subheader("Tickets by category")
        rows = {
            "Category": [c.value for c in s.by_category],
            "Tickets": list(s.by_category.values()),
        }
        st.bar_chart(
            rows, x="Category", y="Tickets",
            x_label="Category", y_label="Number of tickets",
        )
        st.table(rows)
