"""Security-hardening tests for review fixes F-02/F-03/F-05/F-06/F-10/F-11/F-12.

Covers AC-034..AC-037 and NFR-013..NFR-017 (requirements v3).
"""

import logging
import os
import stat
import sys
import unicodedata
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app import common
from ticketing import db, service, validation
from ticketing.config import DB_ENV_VAR, SEARCH_MAX, get_db_path
from ticketing.exceptions import DatabaseError, ValidationError
from ticketing.models import TicketFilter

ROOT = Path(__file__).resolve().parent.parent
MAIN = str(ROOT / "app" / "main.py")

posix_only = pytest.mark.skipif(
    not sys.platform.startswith(("linux", "darwin")) or os.name != "posix",
    reason="POSIX file modes are not meaningful on this platform",
)

# --------------------------------------------------------------------------- NFR-013 / AC-035
BAD_CHARS = {
    "nul": "\x00",
    "c0_bell": "\x07",
    "del": "\x7f",
    "c1_80": "\x80",
    "c1_8d": "\x8d",
    "c1_9f": "\x9f",
    "zwsp": "\u200b",
    "zwnj": "\u200c",
    "zwj": "\u200d",
    "word_joiner": "\u2060",
    "bom": "\ufeff",
    "lre": "\u202a",
    "rle": "\u202b",
    "pdf": "\u202c",
    "lro": "\u202d",
    "rlo": "\u202e",
    "lri": "\u2066",
    "rli": "\u2067",
    "fsi": "\u2068",
    "pdi": "\u2069",
}
BAD_PARAMS = list(BAD_CHARS.values())
BAD_IDS = list(BAD_CHARS)

_GOOD = {
    "title": "Printer",
    "description": "Jams often",
    "category": "Hardware",
    "priority": "Low",
    "creator": "alice",
}


def _mid(field_value: str, ch: str) -> str:
    """Embed ``ch`` in the middle of a value (not trimmed by str.strip)."""
    return f"{field_value[:2]}{ch}{field_value[2:]}"


@pytest.mark.req("NFR-013", "AC-035")
@pytest.mark.parametrize("ch", BAD_PARAMS, ids=BAD_IDS)
@pytest.mark.parametrize("field", ["title", "description", "creator"])
def test_create_rejects_bad_chars_naming_field_ac035(db_path, field, ch):
    args = dict(_GOOD)
    args[field] = _mid(_GOOD[field], ch)
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(db_path, **args)
    assert ei.value.field == field
    assert service.list_tickets(db_path) == []  # nothing stored


@pytest.mark.req("NFR-013", "AC-035")
@pytest.mark.parametrize("ch", BAD_PARAMS, ids=BAD_IDS)
def test_resolution_note_update_rejects_bad_chars_ac035(db_path, make_ticket, ch):
    t = make_ticket()
    with pytest.raises(ValidationError) as ei:
        service.update_resolution_note(db_path, t.id, _mid("fixed it", ch))
    assert ei.value.field == "resolution_note"
    assert service.get_ticket(db_path, t.id).resolution_note is None


@pytest.mark.req("NFR-013", "AC-035")
@pytest.mark.parametrize("ch", BAD_PARAMS, ids=BAD_IDS)
def test_status_change_note_rejects_bad_chars_ac035(db_path, make_ticket, ch):
    t = make_ticket()
    with pytest.raises(ValidationError) as ei:
        service.update_status(db_path, t.id, "Resolved", _mid("fixed it", ch))
    assert ei.value.field == "resolution_note"
    assert service.get_ticket(db_path, t.id).status.value == "Open"


@pytest.mark.req("NFR-013", "AC-035", "NFR-014", "AC-034")
@pytest.mark.parametrize("ch", BAD_PARAMS, ids=BAD_IDS)
def test_search_rejects_bad_chars_ac035(db_path, ch):
    with pytest.raises(ValidationError) as ei:
        service.list_tickets(db_path, TicketFilter(search=_mid("printer", ch)))
    assert ei.value.field == "search"


@pytest.mark.req("NFR-013", "AC-035")
@pytest.mark.parametrize("ch", BAD_PARAMS, ids=BAD_IDS)
def test_creator_lookup_rejects_bad_chars_ac035(db_path, ch):
    with pytest.raises(ValidationError) as ei:
        service.list_tickets_for_creator(db_path, _mid("alice", ch))
    assert ei.value.field == "creator"


@pytest.mark.req("NFR-013", "AC-035")
@pytest.mark.parametrize("ch", ["\u200b", "\u202e", "\x9f", "\x00"])
def test_bad_char_at_edges_rejected_ac035(db_path, ch):
    """Zero-width/bidi/C1/NUL are not whitespace, so they survive strip() and are rejected."""
    for value in (ch + "abc", "abc" + ch):
        with pytest.raises(ValidationError):
            validation.validate_title(value)


@pytest.mark.req("NFR-013", "AC-035")
def test_leading_c1_nel_is_stripped_as_whitespace_ac035():
    """Documented behaviour: U+0085 (NEL) is whitespace to str.strip, so a LEADING or
    TRAILING \\x85 is trimmed away before the control-char check; a MIDDLE one is rejected.
    """
    assert "\x85".isspace()
    assert validation.validate_title("\x85abc") == "abc"
    assert validation.validate_title("abc\x85") == "abc"
    with pytest.raises(ValidationError):
        validation.validate_title("ab\x85c")


@pytest.mark.req("NFR-013", "AC-035")
@pytest.mark.parametrize("field", ["description", "resolution_note"])
def test_newline_cr_tab_allowed_in_multiline_fields_ac035(db_path, make_ticket, field):
    text = "line one\nline two\r\n\tindented"
    if field == "description":
        t = make_ticket(description=text)
        assert service.get_ticket(db_path, t.id).description == text
    else:
        t = make_ticket()
        out = service.update_resolution_note(db_path, t.id, text)
        assert out.resolution_note == text


@pytest.mark.req("NFR-013", "AC-035")
def test_newline_tab_allowed_in_title_and_search_current_behaviour_ac035(db_path):
    """Validator allows \\n \\r \\t in every free-text field (as built, NFR-013 wording)."""
    t = service.create_ticket(db_path, **{**_GOOD, "title": "a\tb\nc"})
    assert t.title == "a\tb\nc"
    assert validation.validate_search("a\tb") == "a\tb"


@pytest.mark.req("NFR-013", "AC-035")
def test_ordinary_unicode_still_accepted_ac035(db_path):
    args = {**_GOOD, "title": "Drücker kaputt 日本語 🙂", "creator": "Élise"}
    t = service.create_ticket(db_path, **args)
    assert t.title == "Drücker kaputt 日本語 🙂"


@pytest.mark.req("NFR-013", "AC-035")
def test_creator_case_insensitive_unicode_ac035(db_path, make_ticket):
    make_ticket(creator="élise")
    for name in ("ÉLISE", "Élise", "élise"):
        assert len(service.list_tickets_for_creator(db_path, name)) == 1, name


@pytest.mark.req("NFR-013", "AC-035")
def test_creator_nfc_nfd_equivalence_ac035(db_path, make_ticket):
    nfc = unicodedata.normalize("NFC", "élise")
    nfd = unicodedata.normalize("NFD", "élise")
    assert nfc != nfd
    make_ticket(creator=nfc)
    assert len(service.list_tickets_for_creator(db_path, nfd)) == 1
    assert len(service.list_tickets_for_creator(db_path, nfd.upper())) == 1


@pytest.mark.req("NFR-013", "AC-035")
def test_creator_casefold_sharp_s_ac035(db_path, make_ticket):
    make_ticket(creator="Straße")
    assert len(service.list_tickets_for_creator(db_path, "STRASSE")) == 1


@pytest.mark.req("NFR-013", "AC-035")
def test_creator_different_names_not_matched_ac035(db_path, make_ticket):
    make_ticket(creator="élise")
    assert service.list_tickets_for_creator(db_path, "elise") == []


# --------------------------------------------------------------------------- NFR-014 / AC-034
@pytest.mark.req("NFR-014", "AC-034")
def test_search_length_100_ok_101_rejected_ac034(db_path, make_ticket):
    assert SEARCH_MAX == 100
    make_ticket(title="x" * 100, description="d")
    assert len(service.list_tickets(db_path, TicketFilter(search="x" * 100))) == 1
    with pytest.raises(ValidationError) as ei:
        service.list_tickets(db_path, TicketFilter(search="x" * 101))
    assert ei.value.field == "search"
    assert "100" in ei.value.message


@pytest.mark.req("NFR-014", "AC-034")
def test_search_length_counted_after_trim_ac034():
    assert validation.validate_search("  " + "x" * 100 + "  ") == "x" * 100
    with pytest.raises(ValidationError):
        validation.validate_search("x" * 101)


@pytest.mark.req("NFR-014", "AC-034")
def test_search_substring_case_insensitive_title_and_description_ac034(db_path, make_ticket):
    a = make_ticket(title="Printer jam", description="floor 3")
    b = make_ticket(title="Mouse", description="the PRINTER is fine")
    make_ticket(title="Screen", description="flicker")
    ids = {t.id for t in service.list_tickets(db_path, TicketFilter(search="pRiNtEr"))}
    assert ids == {a.id, b.id}
    assert {t.id for t in service.list_tickets(db_path, TicketFilter(search="int"))} == {a.id, b.id}


@pytest.mark.req("NFR-014", "AC-034")
@pytest.mark.parametrize(
    ("needle", "hay_match", "hay_other"),
    [("100%", "Disk 100% full", "Disk 1000 full"),
     ("a_b", "file a_b here", "file aXb here"),
     ("c:\\tmp", "path c:\\tmp bad", "path c:tmp bad")],
)
def test_search_special_chars_literal_ac034(db_path, make_ticket, needle, hay_match, hay_other):
    m = make_ticket(title=hay_match)
    make_ticket(title=hay_other)
    got = service.list_tickets(db_path, TicketFilter(search=needle))
    assert [t.id for t in got] == [m.id]


@pytest.mark.req("NFR-014", "AC-034", "AC-025")
def test_search_sql_like_text_is_plain_and_table_intact_ac034(db_path, make_ticket):
    make_ticket(title="normal")
    needle = "'; DROP TABLE tickets;--"
    assert service.list_tickets(db_path, TicketFilter(search=needle)) == []
    hit = make_ticket(title=f"weird {needle} title")
    assert [t.id for t in service.list_tickets(db_path, TicketFilter(search=needle))] == [hit.id]
    assert len(service.list_tickets(db_path)) == 2


@pytest.mark.req("NFR-014", "AC-034")
def test_search_combined_with_filters_ac034(db_path, make_ticket):
    keep = make_ticket(title="net down", category="Network", priority="High")
    make_ticket(title="net slow", category="Network", priority="Low")
    make_ticket(title="net other", category="Access", priority="High")
    flt = TicketFilter(priority="High", category="Network", search="NET")
    assert [t.id for t in service.list_tickets(db_path, flt)] == [keep.id]
    service.update_status(db_path, keep.id, "In Progress")
    assert service.list_tickets(db_path, TicketFilter(status="Open", search="net down")) == []


@pytest.mark.req("NFR-014", "AC-034")
def test_search_no_match_returns_empty_ac034(db_path, make_ticket):
    make_ticket()
    assert service.list_tickets(db_path, TicketFilter(search="zzzznomatch")) == []


@pytest.mark.req("NFR-014", "AC-034")
def test_ui_search_no_match_shows_empty_state_ac034(db_path, monkeypatch, make_ticket):
    make_ticket()
    monkeypatch.setenv(DB_ENV_VAR, str(db_path))
    at = AppTest.from_file(MAIN, default_timeout=30)
    at.run()
    at.sidebar.selectbox(key="role").select("Support Engineer").run()
    at.text_input(key="all_search").input("zzzznomatch").run()
    assert not at.exception
    assert any("No tickets match" in i.value for i in at.info)


@pytest.mark.req("NFR-014", "AC-034")
@pytest.mark.ui
def test_ui_search_input_has_max_chars_ac034(db_path, monkeypatch):
    monkeypatch.setenv(DB_ENV_VAR, str(db_path))
    at = AppTest.from_file(MAIN, default_timeout=30)
    at.run()
    at.sidebar.selectbox(key="role").select("Support Engineer").run()
    assert at.text_input(key="all_search").max_chars == SEARCH_MAX
    src = (ROOT / "app" / "views_list.py").read_text(encoding="utf-8")
    assert "max_chars=SEARCH_MAX" in src


# --------------------------------------------------------------------------- NFR-015 (F-10)
@pytest.mark.req("NFR-015", "AC-036")
@pytest.mark.parametrize("kind", ["proc", "under_file", "file_as_dir"])
def test_bad_db_path_generic_database_error_without_path_nfr015(tmp_path, monkeypatch, kind):
    if kind == "proc":
        bad = "/proc/x/y.db"
    else:
        f = tmp_path / "afile"
        f.write_text("x")
        bad = str(f / "sub" / "y.db") if kind == "under_file" else str(f / "y.db")
    monkeypatch.setenv(DB_ENV_VAR, bad)
    with pytest.raises(DatabaseError) as ei:
        service.init_database(get_db_path())
    msg = str(ei.value)
    assert msg and bad not in msg and "/proc" not in msg and "afile" not in msg
    assert ei.value.message == DatabaseError().message  # generic text
    assert str(tmp_path) not in msg


@pytest.mark.req("NFR-015", "AC-036")
@posix_only
def test_new_db_file_mode_0600_nfr015(tmp_path):
    path = tmp_path / "fresh.db"
    service.init_database(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO) == 0


@pytest.mark.req("NFR-015", "AC-036")
@posix_only
def test_new_db_created_by_write_path_mode_0600_nfr015(tmp_path):
    old = os.umask(0o000)  # permissive umask must not widen the mode
    try:
        path = tmp_path / "w.db"
        service.init_database(path)
        service.create_ticket(path, **_GOOD)
    finally:
        os.umask(old)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.req("NFR-015", "AC-036")
@posix_only
def test_new_data_dir_mode_0700_nfr015(tmp_path, monkeypatch):
    old = os.umask(0o000)
    try:
        target = tmp_path / "newdata" / "t.db"
        monkeypatch.setenv(DB_ENV_VAR, str(target))
        p = get_db_path()
    finally:
        os.umask(old)
    assert p == target
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700


@pytest.mark.req("NFR-015")
@posix_only
def test_existing_db_file_mode_not_changed_nfr015(tmp_path):
    path = tmp_path / "pre.db"
    path.write_bytes(b"")
    path.chmod(0o640)
    service.init_database(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


# --------------------------------------------------------------------------- F-11
class _FailingRollbackConn:
    """Proxy around a sqlite3 connection whose ROLLBACK statement fails."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, *a):
        import sqlite3

        if sql.strip().upper() == "ROLLBACK":
            raise sqlite3.OperationalError("rollback boom")
        return self._conn.execute(sql, *a)

    def close(self):
        self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.mark.req("NFR-004", "NFR-017")
def test_failing_rollback_does_not_mask_original_exception_f11(db_path, monkeypatch, caplog):
    real_open = db._open
    monkeypatch.setattr(db, "_open", lambda p: _FailingRollbackConn(real_open(p)))

    class Marker(Exception):
        pass

    with caplog.at_level(logging.ERROR, logger="ticketing.db"), pytest.raises(Marker):
        with db.transaction(db_path):
            raise Marker("original")
    assert any("Rollback failed" in r.getMessage() for r in caplog.records)


@pytest.mark.req("NFR-004", "NFR-017")
def test_failing_rollback_keeps_typed_validation_error_f11(db_path, make_ticket, monkeypatch):
    t = make_ticket()
    real_open = db._open
    monkeypatch.setattr(db, "_open", lambda p: _FailingRollbackConn(real_open(p)))
    with pytest.raises(Exception) as ei:  # noqa: B017
        service.update_status(db_path, t.id, "Closed")  # Open -> Closed not allowed
    assert type(ei.value).__name__ == "InvalidTransitionError"


# --------------------------------------------------------------------------- NFR-016 / NFR-017
def _config_text() -> str:
    return (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")


@pytest.mark.req("NFR-016", "NFR-017", "AC-036")
def test_streamlit_config_hardened_nfr016_ac036():
    import tomllib

    cfg = tomllib.loads(_config_text())
    assert cfg["server"]["address"] == "127.0.0.1"
    assert cfg["server"]["enableXsrfProtection"] is True
    assert cfg["server"]["enableCORS"] is True
    assert cfg["client"]["showErrorDetails"] == "none"
    assert cfg["browser"]["gatherUsageStats"] is False


@pytest.mark.req("NFR-017", "AC-036")
def test_plain_escapes_markdown_and_html_f12():
    out = common.plain(
        "**bold** _it_ [x](http://e.com) `c` <b>h</b> # h > q | t ~s~ $m$ \\ & :smile:"
    )
    for ch in "*_[]()`<>#|~$\\&:":
        # every special char in output must be preceded by a backslash
        idxs = [i for i, c in enumerate(out) if c == ch]
        for i in idxs:
            if ch == "\\":
                continue
            assert out[i - 1] == "\\", (ch, out)
    assert common.plain("plain words") == "plain words"
    assert common.plain("") == ""


@pytest.mark.req("NFR-017", "AC-036")
@pytest.mark.ui
def test_creating_as_line_not_rendered_as_markdown_f12(db_path, monkeypatch):
    monkeypatch.setenv(DB_ENV_VAR, str(db_path))
    raw = "**Bob** [click](http://evil.example) <b>x</b>"
    at = AppTest.from_file(MAIN, default_timeout=30)
    at.run()
    at.sidebar.text_input(key="requester_name").input(raw).run()
    assert not at.exception
    assert not any(raw in m.value for m in at.markdown)
    assert not any(raw in c.value for c in at.caption)
    # rendered as a plain st.text element carrying the literal name
    assert any(raw in t.value for t in at.text)


@pytest.mark.req("NFR-017", "AC-036")
@pytest.mark.ui
def test_main_broad_except_logs_and_shows_generic_message_f02_f03(
    db_path, monkeypatch, caplog
):
    secret = "SECRET-INTERNAL-PATH /etc/shadow"

    def boom() -> None:
        raise RuntimeError(secret)

    monkeypatch.setattr(common, "get_path", boom)
    at = AppTest.from_file(MAIN, default_timeout=30)
    with caplog.at_level(logging.ERROR):
        at.run()
    assert not at.exception  # no traceback element in the page
    assert any("could not be opened" in e.value for e in at.error)
    assert all(secret not in e.value for e in at.error)
    assert all(secret not in str(x.value) for x in at.markdown)
    assert any("Database bootstrap failed" in r.getMessage() for r in caplog.records)
    assert all(secret not in r.getMessage() for r in caplog.records)


@pytest.mark.req("NFR-017", "AC-036", "NFR-015")
@pytest.mark.ui
def test_main_bad_db_path_shows_generic_error_without_path_f10(monkeypatch):
    bad = "/proc/x/y.db"
    monkeypatch.setenv(DB_ENV_VAR, bad)
    at = AppTest.from_file(MAIN, default_timeout=30)
    at.run()
    assert not at.exception
    assert at.error
    assert all("/proc" not in e.value and bad not in e.value for e in at.error)


# --------------------------------------------------------------------------- AC-037 / NFR-009
def _norm(text: str) -> str:
    return " ".join(text.lower().split())


@pytest.mark.req("NFR-009", "AC-037")
@pytest.mark.parametrize("doc", ["README.md", "docs/architecture.md"])
def test_docs_state_demo_not_auth_and_no_public_deploy_ac037(doc):
    text = _norm((ROOT / doc).read_text(encoding="utf-8"))
    assert "not authentication" in text
    assert "not authorization" in text
    assert "demo" in text
    assert "publicly deployed" in text
    assert "multi-user" in text
