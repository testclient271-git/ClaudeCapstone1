"""Tests for security fixes N-01 (loopback guard), N-02 (format chars), N-03 (selectbox label).

Covers NFR-009, NFR-013, NFR-016, NFR-017 (AC-035, AC-036, AC-037).
"""

from pathlib import Path

import pytest
import streamlit
from streamlit.testing.v1 import AppTest

from ticketing import service, validation
from ticketing.exceptions import ValidationError

ROOT = Path(__file__).resolve().parent.parent
MAIN = str(ROOT / "app" / "main.py")


# ----------------------------------------------------------------------------- N-01
def _load_guard():
    """Load is_loopback_address WITHOUT importing app.main.

    Importing app.main runs main() at module level, which bootstraps the real
    data/tickets.db (see DEF-003 in reports/test-report.md), so the helper and its
    constant are extracted from the source instead.
    """
    import ast

    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    keep = [
        n for n in ast.parse(src).body
        if (isinstance(n, ast.FunctionDef) and n.name == "is_loopback_address")
        or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "LOOPBACK_ADDRESSES")
    ]
    ns: dict = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app/main.py", "exec"), ns)  # noqa: S102
    return ns["is_loopback_address"]


is_loopback_address = _load_guard()


@pytest.mark.req("NFR-016", "NFR-009", "N-01")
@pytest.mark.parametrize("addr", [
    "127.0.0.1", "::1", "localhost", "LOCALHOST", "LocalHost", "[::1]", "[127.0.0.1]",
    " 127.0.0.1 ",
])
def test_is_loopback_true_n01(addr):
    assert is_loopback_address(addr) is True


@pytest.mark.req("NFR-016", "NFR-009", "N-01")
@pytest.mark.parametrize("addr", [
    "", None, 0, 127, b"127.0.0.1", ["127.0.0.1"], "0.0.0.0", "::", "192.168.1.5",
    "example.com", "127.0.0.2", "localhost.example.com", "[::]",
])
def test_is_loopback_false_n01(addr):
    assert is_loopback_address(addr) is False


def _patched_app(monkeypatch, address) -> AppTest:
    real = streamlit.get_option

    def fake(key):
        return address if key == "server.address" else real(key)

    monkeypatch.setattr(streamlit, "get_option", fake)
    at = AppTest.from_file(MAIN, default_timeout=30)
    at.run()
    return at


@pytest.mark.req("NFR-016", "NFR-009", "N-01")
@pytest.mark.parametrize("addr", ["0.0.0.0", "", None, "192.168.1.5", "example.com", "::"])
def test_guard_blocks_non_loopback_n01(db_path, monkeypatch, addr):
    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    service.create_ticket(
        db_path, title="SECRET-TITLE-XYZ", description="d", category="Hardware",
        priority="Low", creator="alice",
    )
    at = _patched_app(monkeypatch, addr)
    assert not at.exception
    assert len(at.error) == 1
    assert "not loopback" in at.error[0].value
    assert "--server.address 127.0.0.1" in at.error[0].value
    # no role views, no ticket data
    assert len(at.sidebar.selectbox) == 0
    assert len(at.selectbox) == 0
    assert len(at.tabs) == 0
    assert len(at.dataframe) == 0
    assert len(at.warning) == 0
    everything = " ".join(
        str(e.value) for coll in (at.markdown, at.text, at.caption, at.error, at.info)
        for e in coll
    )
    assert "SECRET-TITLE-XYZ" not in everything


@pytest.mark.req("NFR-016", "NFR-009", "N-01")
@pytest.mark.parametrize("addr", ["127.0.0.1", "localhost", "::1"])
def test_guard_allows_loopback_n01(db_path, monkeypatch, addr):
    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    at = _patched_app(monkeypatch, addr)
    assert not at.exception
    assert len(at.error) == 0
    assert list(at.sidebar.selectbox(key="role").options) == [
        "Employee", "Support Engineer", "Manager",
    ]


@pytest.mark.req("NFR-016", "NFR-009", "N-01")
def test_readme_run_commands_loopback_and_repo_root_n01():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    run_lines = [ln for ln in text.splitlines() if "streamlit run" in ln]
    assert run_lines, "README has no run command"
    for ln in run_lines:
        assert "--server.address 127.0.0.1" in ln, ln
    assert "repository root" in text.lower()


# ----------------------------------------------------------------------------- N-02
N02_CHARS = {
    "lrm_200e": "‎", "rlm_200f": "‏", "shy_00ad": "­",
    "ls_2028": " ", "ps_2029": " ", "alm_061c": "؜", "mvs_180e": "᠎",
    "tag_e0000": "\U000e0000", "tag_e0041": "\U000e0041", "tag_e007f": "\U000e007f",
    "cf_2061": "⁡", "cf_206a": "⁪", "cf_feff": "﻿", "cf_0600": "؀",
    "cf_110bd": "\U000110bd",
}
FIELD_CALLS = {
    "title": validation.validate_title,
    "description": validation.validate_description,
    "creator": validation.validate_creator,
    "resolution_note": validation.validate_resolution_note,
    "search": validation.validate_search,
}


@pytest.mark.req("NFR-013", "AC-035", "N-02")
@pytest.mark.parametrize("field", list(FIELD_CALLS))
@pytest.mark.parametrize("ch", list(N02_CHARS.values()), ids=list(N02_CHARS))
def test_format_chars_rejected_with_field_n02(field, ch):
    texts = [f"ab{ch}cd"]
    if not ch.isspace():  # str.strip() legitimately trims leading/trailing U+2028/2029
        texts += [f"ab{ch}", f"{ch}ab"]
    for text in texts:
        with pytest.raises(ValidationError) as ei:
            FIELD_CALLS[field](text)
        assert ei.value.field == field


@pytest.mark.req("NFR-013", "AC-035", "N-02")
def test_all_cf_zl_zp_chars_rejected_exhaustive_n02():
    import sys
    import unicodedata

    missed = [
        hex(o) for o in range(sys.maxunicode + 1)
        if unicodedata.category(chr(o)) in ("Cf", "Zl", "Zp")
        and not _rejected(chr(o))
    ]
    assert missed == []


def _rejected(ch: str) -> bool:
    try:
        validation.validate_description(f"a{ch}b")
    except ValidationError:
        return True
    return False


@pytest.mark.req("NFR-013", "AC-035", "N-02")
@pytest.mark.parametrize("field", list(FIELD_CALLS))
@pytest.mark.parametrize("text", [
    "Élise café naïve", "Straße ñandú", "日本語のテキスト", "Printer \U0001F600 broken",
    "line1\nline2", "tab\there", "Ünïcödé 中文",
])
def test_normal_text_still_accepted_n02(field, text):
    assert FIELD_CALLS[field](text) == text.strip()


@pytest.mark.req("NFR-013", "AC-035", "N-02")
def test_service_create_rejects_lrm_in_title_n02(db_path):
    with pytest.raises(ValidationError) as ei:
        service.create_ticket(
            db_path, title="Pay‎ment", description="d", category="Hardware",
            priority="Low", creator="alice",
        )
    assert ei.value.field == "title"


# ----------------------------------------------------------------------------- N-03
@pytest.mark.req("NFR-017", "AC-036", "N-03")
def test_engineer_selectbox_label_escapes_markdown_n03(db_path, monkeypatch):
    from app.common import plain

    monkeypatch.setenv("TICKETS_DB_PATH", str(db_path))
    title = "![x](http://e/x.png) **b**"
    t = service.create_ticket(
        db_path, title=title, description="d", category="Hardware",
        priority="Low", creator="alice",
    )
    at = AppTest.from_file(MAIN, default_timeout=30)
    at.run()
    at.sidebar.selectbox(key="role").select("Support Engineer")
    at.run()
    assert not at.exception
    sb = at.selectbox(key="selected_ticket_id")
    label = sb.format_func(t.id) if callable(getattr(sb, "format_func", None)) else sb.options[0]
    assert label == plain(f"#{t.id} - {title} [{t.status.value}]")
    assert "![x](" not in label and "**b**" not in label
    assert "\\!\\[x\\]\\(" in label
    assert "\\*\\*b\\*\\*" in label
