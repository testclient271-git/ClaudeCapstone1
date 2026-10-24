"""Pure input validation and normalisation (FR-003, FR-010, NFR-002; architecture section 7).

No I/O. Every failure raises ``ValidationError`` naming the field with a plain-language,
user-safe message. Strings are trimmed before checks.
"""

from __future__ import annotations

import unicodedata
from enum import Enum
from typing import TypeVar

from ticketing.config import (
    CREATOR_MAX,
    DESCRIPTION_MAX,
    RESOLUTION_NOTE_MAX,
    SEARCH_MAX,
    TITLE_MAX,
)
from ticketing.exceptions import InvalidTransitionError, ValidationError
from ticketing.models import ALLOWED_TRANSITIONS, Category, Priority, Status

E = TypeVar("E", bound=Enum)

_ALLOWED_CONTROL = frozenset("\n\r\t")


_INVISIBLE = frozenset("\u200b\u200c\u200d\u2060\ufeff")
_BIDI = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
_EXTRA_BAD = frozenset("\u200e\u200f\u00ad\u2028\u2029\u061c\u180e")
_BAD_CATEGORIES = frozenset({"Cf", "Zl", "Zp"})


def _has_bad_char(text: str) -> bool:
    """True if ``text`` has C0/C1 controls (except newline/CR/tab), zero-width or bidi chars."""
    for ch in text:
        o = ord(ch)
        if ch in _ALLOWED_CONTROL:
            continue
        if o < 32 or 127 <= o <= 159 or ch in _INVISIBLE or ch in _BIDI:
            return True
        if ch in _EXTRA_BAD or 0xE0000 <= o <= 0xE007F:
            return True
        if unicodedata.category(ch) in _BAD_CATEGORIES:
            return True
    return False


def _clean_text(field: str, value: object, label: str) -> str:
    """Return ``value`` trimmed; reject non-strings and disallowed control characters."""
    if not isinstance(value, str):
        raise ValidationError(field, f"{label} must be text.")
    text = value.strip()
    if _has_bad_char(text):
        raise ValidationError(field, f"{label} contains characters that are not allowed.")
    return text


def _required_text(field: str, value: object, label: str, required_msg: str, max_len: int) -> str:
    """Validate a required, length-bounded text field (AC-002, AC-003)."""
    text = _clean_text(field, value, label)
    if not text:
        raise ValidationError(field, required_msg)
    if len(text) > max_len:
        raise ValidationError(field, f"{label} must be {max_len} characters or fewer.")
    return text


def validate_title(value: object) -> str:
    """Return the trimmed title, 1-100 chars (FR-003, AC-002/003)."""
    return _required_text("title", value, "Title", "Title is required.", TITLE_MAX)


def validate_description(value: object) -> str:
    """Return the trimmed description, 1-2000 chars (FR-003, AC-002/003)."""
    return _required_text(
        "description", value, "Description", "Description is required.", DESCRIPTION_MAX
    )


def validate_creator(value: object) -> str:
    """Return the trimmed creator name, 1-100 chars (FR-001, FR-005, D-03)."""
    return _required_text("creator", value, "Name", "Your name is required.", CREATOR_MAX)


def validate_resolution_note(value: object) -> str:
    """Return a trimmed, non-blank resolution note, at most 2000 chars (FR-021, D-04)."""
    return _required_text(
        "resolution_note",
        value,
        "Resolution note",
        "A resolution note is required.",
        RESOLUTION_NOTE_MAX,
    )


def optional_resolution_note(value: object) -> str | None:
    """Return a validated note, or ``None`` when absent or blank (used by update_status)."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return validate_resolution_note(value)


def _coerce_enum(enum_cls: type[E], field: str, label: str, value: object) -> E:
    """Accept an enum member or its string value; otherwise raise ``ValidationError``."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value.strip())
        except ValueError:
            pass
    options = ", ".join(str(m.value) for m in enum_cls)
    raise ValidationError(field, f"{label} must be one of: {options}.")


def coerce_status(value: object) -> Status:
    """Return a ``Status`` from a member or string (FR-010, AC-014)."""
    return _coerce_enum(Status, "status", "Status", value)


def coerce_priority(value: object) -> Priority:
    """Return a ``Priority`` from a member or string (FR-002, AC-005)."""
    return _coerce_enum(Priority, "priority", "Priority", value)


def coerce_category(value: object) -> Category:
    """Return a ``Category`` from a member or string (D-01, FR-001)."""
    return _coerce_enum(Category, "category", "Category", value)


def validate_ticket_id(value: object) -> int:
    """Return ``value`` if it is an integer >= 1 (bool and other types rejected)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError("ticket_id", "Ticket ID must be a positive whole number.")
    return value


def validate_search(value: object) -> str | None:
    """Return a trimmed search term, or ``None`` if absent or blank (FR-006)."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError("search", "Search text must be text.")
    text = value.strip()
    if _has_bad_char(text):
        raise ValidationError("search", "Search text contains characters that are not allowed.")
    if len(text) > SEARCH_MAX:
        raise ValidationError("search", f"Search text must be {SEARCH_MAX} characters or fewer.")
    return text or None


def check_transition(current: Status, requested: Status) -> None:
    """Raise ``InvalidTransitionError`` unless the move is allowed (D-02, FR-010, AC-014)."""
    if requested not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(current, requested)


def require_note_for_resolved(
    requested: Status, supplied: str | None, stored: str | None
) -> str | None:
    """Return the note to store; Resolved needs a supplied or stored non-blank note (D-04).

    Returns ``supplied`` (possibly ``None`` meaning keep the stored note).
    """
    if requested is Status.RESOLVED and not supplied and not (stored and stored.strip()):
        raise ValidationError(
            "resolution_note", "A resolution note is required to resolve a ticket."
        )
    return supplied
