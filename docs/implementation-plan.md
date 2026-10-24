# Implementation Plan

Status: APPROVED and implemented; reconciled with the as-built code (see "As-built deviations" below and architecture section 14). Installing streamlit, pytest, ruff required separate human approval (checkpoint 3).

Agents: BE = backend-developer, FE = frontend-developer, QA = qa-engineer, SEC = security-reviewer. Requirement IDs refer to `docs/requirements.md` (category, resolution note and four-status dashboard are now FR-020/FR-021/FR-013/FR-014; the former REQ-DELTA markers are resolved).

## Ordered tasks

| # | Task | Owner | Requirements | Depends on |
|---|---|---|---|---|
| T0 | Approve dependency install (streamlit, pytest, ruff); create venv and `requirements.txt` | human, BE | NFR-008 | approvals |
| T1 | `ticketing/models.py`, `exceptions.py`, `config.py`: enums, DTOs, exceptions, DB path, `ALLOWED_TRANSITIONS`; signature-only `service.py` skeleton (the frozen contract) | BE | FR-002, FR-010, NFR-007 | T0 |
| T2 | `pyproject.toml` with pytest markers and Ruff config; `tests/conftest.py` fixtures (tmp DB) | QA | NFR-008 | T0 |
| T3 | `db.py`: DDL, `init_db`, `user_version`, `connect`; `.gitignore` for `data/`, `*.db` | BE | FR-017, NFR-003, NFR-004 | T1 |
| T4 | `validation.py` pure functions and messages | BE | FR-003, NFR-002, AC-002/003/005 | T1 |
| T5 | `repository.py`: insert, fetch, query with filters, update, counts; parameterized only | BE | FR-001..011, FR-012..015, NFR-004 | T3 |
| T6 | `service.py`: all functions in architecture section 5.3, transaction handling, error mapping | BE | FR-001..016, D-04 | T4, T5 |
| T7 | Service/repo/schema tests written from the contract (can start after T1/T2, run green after T6): AC-001..021, AC-025, AC-026, enum/DDL parity, architecture static scan | QA | NFR-008, all AC | T1, T2 (run: T6) |
| T8 | (Obsolete, not executed: no stub service was used; UI was built against the real `ticketing.service`) | n/a | n/a | n/a |
| T9 | `app/main.py`, `app/common.py`: role selector, DEMO banner, routing, cached DB init | FE | FR-018, FR-019, FR-022, NFR-009, AC-022/023/031 | T1 |
| T10 | `app/views_employee.py`: create form, "My tickets" | FE | FR-001..005, NFR-001/002 | T9 |
| T11 | `app/views_list.py`, `app/views_engineer.py`: list with filters and search, detail, status/priority/note updates | FE | FR-006..011, FR-021 | T9 |
| T12 | `app/views_manager.py`: metrics, priority and category tables | FE | FR-012..016, FR-020 | T9 |
| T13 | (Merged into T9..T12: UI calls real service directly) smoke run | FE | all | T6, T10..T12 |
| T14 | `README.md`: run steps, DB path, DEMO disclosure | BE | NFR-009, AC-023 | T6 |
| T15 | Optional `AppTest` smoke tests, manual checklist for AC-022/024/028; `ruff check .` and full `pytest -v` evidence | QA | AC-022..024, 027, 028 | T13 |
| T16 | Human checkpoint 4: implementation complete | orchestrator | | T15 |
| T17 | Security review (SQL injection, XSS via text rendering, DEMO disclosure, path/config, dependencies) | SEC | NFR-004, NFR-009 | T16 |
| T18 | Defect fixes by owning dev, retest by QA/SEC; update traceability test column | BE/FE, QA | | T17 |
| T19 | Final acceptance | human | | T18 |

## Parallelization
- After T1 (contract frozen): BE track (T3 to T6, T14), FE track (T8 to T12) and QA track (T2, T7) run in parallel.
- FE codes only against `ticketing.service`, `models` and `exceptions` (no stub was used; as built, FE worked against the real service).
- QA tests are written against the contract; red until BE tasks land, then must go green without test weakening.
- Join points: T6 (services real) unblocks T13; T13 unblocks T15.
- Contract changes after T1 need re-approval and are routed through the orchestrator.

## Integration dependencies
- Single shared interface: `ticketing/service.py` signatures, `models.py`, `exceptions.py` (architecture section 5).
- `config.get_db_path()` used via `app/common.py`; tests pass explicit paths.
- Enum values and DDL CHECK lists must stay identical (QA parity test).
- DEMO banner text lives in `app/common.py` (`demo_banner()`); README copies the same wording.
- Launch: `python -m streamlit run app/main.py`; `.streamlit/config.toml` binds 127.0.0.1.

## Definition of done per task
Type hints and docstrings with requirement IDs; Ruff clean; related pytest tests pass with real output shown; no SQL or `sqlite3` import in UI; no edits outside owned files.

## As-built deviations
Full table in `docs/architecture.md` section 14. Summary: UI is `app/` (`main.py`, `common.py`, `views_*.py`) not `app.py`/`ui/`; no stub service (T8, T13 obsolete); `TicketFilter.search` added; `.streamlit/config.toml` binds 127.0.0.1; `pyproject.toml` is QA-owned; `tests/` and `reports/` exist; tests scan `app/**/*.py`.

## Risks
- Residual requirements wording: A-16, A-18, A-02 still marked OPEN in `docs/requirements.md` although decisions D-01..D-04 were approved; `search` filter not reflected in FR-006. Owner: requirements-analyst.
- Open tooling finding F-14 (unpinned dependencies) owned by qa-engineer/backend-developer.
- The app must not be exposed beyond localhost or deployed as a secure multi-user app (DEMO role selector is not authentication or authorization).
- Streamlit rerun behaviour (forms, state): mitigated by DB-as-source-of-truth and per-call connections.
- Free-text creator allows impersonation: accepted and disclosed (DEMO).
