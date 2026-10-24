"""Enums and immutable DTOs shared by the service, repository and UI (architecture 5.1).

Enum values must stay identical to the CHECK lists in the DDL (NFR-004).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    """Ticket lifecycle status (FR-008)."""

    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class Priority(str, Enum):
    """Ticket priority (FR-002, FR-009)."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Category(str, Enum):
    """Fixed ticket category list (D-01, FR-001)."""

    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    NETWORK = "Network"
    ACCESS = "Access"
    OTHER = "Other"


@dataclass(frozen=True)
class Ticket:
    """A support ticket (FR-001, FR-004, FR-007). Timestamps are UTC ISO-8601 with 'Z'."""

    id: int
    title: str
    description: str
    category: Category
    priority: Priority
    status: Status
    creator: str
    created_at: str
    updated_at: str
    resolution_note: str | None


@dataclass(frozen=True)
class TicketFilter:
    """Optional list filters (FR-006). ``None`` means no restriction.

    ``search`` is a case-insensitive substring match over title and description
    (human-approved addition).
    """

    status: Status | None = None
    priority: Priority | None = None
    category: Category | None = None
    search: str | None = None


@dataclass(frozen=True)
class DashboardStats:
    """Manager dashboard figures (FR-012..FR-016, FR-020).

    ``by_priority`` and ``by_category`` contain every level, zeros included.
    """

    total: int
    open: int
    in_progress: int
    resolved: int
    closed: int
    by_priority: dict[Priority, int]
    by_category: dict[Category, int]


ALLOWED_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.OPEN: frozenset({Status.IN_PROGRESS, Status.RESOLVED}),
    Status.IN_PROGRESS: frozenset({Status.RESOLVED}),
    Status.RESOLVED: frozenset({Status.IN_PROGRESS, Status.CLOSED}),
    Status.CLOSED: frozenset(),
}
"""Permitted status transitions (D-02, FR-010)."""
