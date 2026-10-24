"""Typed exceptions raised by the ticketing service layer (architecture section 5.2).

The UI catches ``TicketingError`` subclasses only and shows ``.message``. Covers NFR-002.
"""

from __future__ import annotations

from ticketing.models import Status


class TicketingError(Exception):
    """Base class for all expected ticketing errors."""

    message: str

    def __init__(self, message: str = "") -> None:
        """Store a user-safe message."""
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        """Return the user-safe message."""
        return self.message


class ValidationError(TicketingError):
    """Input failed validation (FR-003, FR-010, NFR-002); ``field`` names the offending field."""

    def __init__(self, field: str, message: str) -> None:
        """Create the error for ``field`` with a user-safe ``message``."""
        super().__init__(message)
        self.field = field


class InvalidTransitionError(TicketingError):
    """A status change is not allowed (FR-010, AC-014)."""

    def __init__(self, current: Status, requested: Status, message: str | None = None) -> None:
        """Create the error; default message is 'Cannot change status from X to Y.'."""
        super().__init__(
            message or f"Cannot change status from {current.value} to {requested.value}."
        )
        self.current = current
        self.requested = requested


class TicketNotFoundError(TicketingError):
    """No ticket exists with the given id (AC-012)."""

    def __init__(self, ticket_id: int, message: str | None = None) -> None:
        """Create the error for ``ticket_id``."""
        super().__init__(message or f"Ticket #{ticket_id} was not found.")
        self.ticket_id = ticket_id


class DatabaseError(TicketingError):
    """Wraps sqlite3.Error; generic user-safe message, original exception is chained."""

    def __init__(self, message: str = "A database error occurred. Please try again.") -> None:
        """Create the error with a generic user-safe message."""
        super().__init__(message)
