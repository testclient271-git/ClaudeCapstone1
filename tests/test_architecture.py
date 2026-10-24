"""Static layering / documentation checks (NFR-007, NFR-009, NFR-010, AC-023, AC-027, AC-033)."""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP_FILES = sorted((ROOT / "app").rglob("*.py"))
TICKETING_FILES = sorted((ROOT / "ticketing").rglob("*.py"))
SQL_RE = re.compile(
    r"\b(SELECT\s.+\sFROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE|"
    r"CREATE\s+TABLE|ALTER\s+TABLE|PRAGMA)\b",
    re.I | re.S,
)


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names |= {f"{node.module}.{a.name}" for a in node.names}
    return names


def _string_literals(path: Path) -> list[str]:
    return [
        n.value for n in ast.walk(ast.parse(path.read_text()))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def test_app_files_found():
    assert len(APP_FILES) >= 6


@pytest.mark.req("NFR-007", "AC-027")
@pytest.mark.parametrize("path", APP_FILES, ids=lambda p: p.name)
def test_app_has_no_sqlite3_or_repository_import_ac027(path):
    imps = _imports(path)
    assert not any(i == "sqlite3" or i.startswith("sqlite3.") for i in imps)
    assert not any("repository" in i or i.endswith(".db") or i == "ticketing.db" for i in imps)


@pytest.mark.req("NFR-007", "AC-027")
@pytest.mark.parametrize("path", APP_FILES, ids=lambda p: p.name)
def test_app_has_no_sql_strings_ac027(path):
    for s in _string_literals(path):
        assert not SQL_RE.search(s), f"SQL-like string in {path.name}: {s!r}"


@pytest.mark.req("NFR-009", "FR-022")
@pytest.mark.parametrize("path", APP_FILES, ids=lambda p: p.name)
def test_app_has_no_unsafe_allow_html(path):
    assert "unsafe_allow_html" not in path.read_text()


@pytest.mark.req("NFR-007")
@pytest.mark.parametrize("path", TICKETING_FILES, ids=lambda p: p.name)
def test_ticketing_has_no_streamlit_import(path):
    assert not any(i == "streamlit" or i.startswith("streamlit.") for i in _imports(path))
    assert "app" not in {i.split(".")[0] for i in _imports(path)}


@pytest.mark.req("NFR-004", "AC-025")
def test_repository_sql_is_static_no_fstring_sql():
    """No f-string / % / .format / concatenation builds SQL in ticketing."""
    for path in TICKETING_FILES:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.JoinedStr):
                txt = ast.unparse(node)
                assert not SQL_RE.search(txt), f"f-string SQL in {path.name}: {txt}"


@pytest.mark.req("NFR-009", "AC-023")
def test_readme_discloses_demo_selector_ac023():
    text = " ".join((ROOT / "README.md").read_text().lower().split())
    assert "demo" in text
    assert "not authentication" in text
    assert "not authorization" in text


@pytest.mark.req("NFR-011", "NFR-010", "AC-033")
def test_requirements_only_approved_deps_ac033():
    names = {
        re.split(r"[<>=!~ ]", line.strip())[0].lower()
        for line in (ROOT / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert names <= {"streamlit", "pytest", "ruff"}


@pytest.mark.req("NFR-010", "AC-033")
def test_no_network_libraries_in_source_ac033():
    banned = {"requests", "urllib", "urllib3", "http", "httpx", "socket", "aiohttp", "smtplib"}
    for path in APP_FILES + TICKETING_FILES:
        tops = {i.split(".")[0] for i in _imports(path)}
        assert not (tops & banned), f"{path.name} imports {tops & banned}"


@pytest.mark.req("NFR-009", "NFR-004")
def test_no_secrets_like_strings_in_source():
    pat = re.compile(r"(password|api[_-]?key|secret|token)\s*=\s*['\"]\w+", re.I)
    for path in APP_FILES + TICKETING_FILES:
        assert not pat.search(path.read_text()), path.name
