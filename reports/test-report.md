# QA Test Report

Date: 2026-10-24. Author: qa-engineer. Scope: ticketing/** and app/** as delivered (app/main.py layout).

## 1. Commands executed (final, after fix-retest cycle 1)
- `python -m ruff check . > reports/ruff-output.txt 2>&1` -> exit 0, output: `All checks passed!`
- `python -m pytest -v > reports/pytest-output.txt 2>&1` -> exit 0, **270 passed, 0 failed, 0 skipped in 13.29 s**
- Safety: `data/tickets.db` is never created; autouse fixture redirects `TICKETS_DB_PATH` to tmp, and a `pytest_sessionfinish` hook fails the run if the real DB is touched.

## 2. Configuration (pyproject.toml)
- pytest: `testpaths=["tests"]`, markers `req(*ids)` and `ui`.
- ruff: target `py310`, line-length 100, select `E,F,I,B,UP,D,S` exactly as architecture section 8, google docstring convention; tests ignore `D`, `S101`, `S608`, `S105`, `S106`. Nothing was loosened for production code.

## 3. Test files (270 test cases incl. parametrized)
| File | Cases | Covers |
|---|---|---|
| tests/test_service_create.py | 78 | creation, required fields, lengths, control chars, enums, trim, unicode |
| tests/test_service_query.py | 50 | get/list/creator lookup, invalid ids, filters, search with % _ \ |
| tests/test_service_update.py | 50 | status/priority/note updates, all 16 transition cells, Closed final, same-status, Resolved note rule, unchanged-on-failure, updated_at (1.1 s sleeps) |
| tests/test_dashboard.py | 6 | counts, zero-fill, empty DB, sums, reflects changes |
| tests/test_persistence_security.py | 36 | persistence, init idempotent, newer schema, injection strings, CHECK constraints, enum parity, 1,000-ticket timing |
| tests/test_architecture.py | 35 | no sqlite3/SQL/repository in app, no unsafe_allow_html, no streamlit in ticketing, README DEMO text, deps, no network imports |
| tests/test_ui_smoke.py | 13 | AppTest: DEMO banner x3 roles, create flow, validation errors, my tickets, engineer update, closed ticket, filter empty state, manager dashboard |
| tests/test_safety.py | 2 | real DB untouched |

## 4. Defects
| ID | Sev | Req | Description / evidence | Owner |
|---|---|---|---|---|
| DEF-001 | Low | NFR-012, AC-032 | 13 ruff violations in `app/` (E501 x9, E402 x3, B905 x1). **Status: FIXED and VERIFIED CLOSED in retest cycle 1** (see section 6). | frontend-developer |

No functional defects were found: all behaviour tests pass against the service layer and UI.

## 5. Observations (not defects) - AWAITING HUMAN CONFIRMATION
- [AWAITING HUMAN CONFIRMATION] Closed is final for status only: priority and resolution note can still be edited on Closed tickets (test_closed_ticket_note_and_priority_still_editable documents the current behaviour). Confirm intent.
- [AWAITING HUMAN CONFIRMATION] Service requires `priority`; the Medium default (A-17) is applied by the UI form only.
- [AWAITING HUMAN CONFIRMATION] AC-024 (browser check) is manual and not yet performed.
- [AWAITING HUMAN CONFIRMATION] AC-028 (form input count) and AC-033 (review) are only partly automated; the AppTest flow checks 4 inputs + submit (limit 5), the rest is manual/review.
- Employee identity is an unverified free-text name (A-02); tested as case-insensitive exact trimmed match.
- Timestamps have 1-second resolution; tests sleep 1.1 s where a change in updated_at must be observable.
- AppTest: widget values inside `st.form` must be set in the same run as the submit click; harness behaviour, not an app bug.

## 6. Fixes applied and retest (cycle 1)
- Cycle 1: DEF-001 fixed by frontend-developer. Independent retest by qa-engineer:
  - Inspection of app/: E402 handled by targeted `# noqa: E402  (must follow sys.path bootstrap)` on the three imports in app/main.py (15, 17, 18) with a reason; B905 fixed with `strict=True` on the 5-vs-5 `zip` in app/views_manager.py (no behaviour change); long lines wrapped (views_engineer.py `st.text(...)`, views_list.py selectboxes, views_manager.py rows/bar_chart) with no logic change. Config in pyproject.toml has no ruff loosening (select E,F,I,B,UP,D,S; line-length 100; tests-only per-file ignores unchanged).
  - Minor note: app/main.py line 17 (the combined import plus noqa comment) exceeds 100 characters but ruff accepts it; cosmetic only.
  - `python -m ruff check .` -> All checks passed!
  - Full regression `python -m pytest -v` -> 270 passed, 0 failed (no tests changed, weakened or skipped).
  - Result: DEF-001 PASS / CLOSED.

## 7. Remaining problems
No open defects. Outstanding: AC-024 manual verification; the observations in section 5 await human confirmation; security review is separate.

## 8. Acceptance-criteria coverage (test file::test names)
| AC | Tests |
|---|---|
| AC-001 | test_service_create::test_create_ticket_happy_path_ac001; test_ui_smoke::test_employee_create_ticket_flow_ac001 |
| AC-002 | test_service_create::test_create_blank_required_text_ac002, test_create_none_required_field_ac002, test_create_blank_category_priority_ac002; test_ui_smoke::test_employee_blank_title_shows_error_ac002 |
| AC-003 | test_service_create::test_create_length_boundaries_ac003, test_create_length_counted_after_trim_ac003 |
| AC-004 | test_service_create::test_create_each_priority_stored_ac004, test_create_priority_is_required_no_default_in_service; AC-005: test_service_create::test_create_invalid_priority_ac005 |
| AC-005 | test_service_create::test_create_invalid_priority_ac005 |
| AC-006 | test_service_create::test_create_two_tickets_unique_ids_ac006 |
| AC-007 | test_service_query::test_list_for_creator_* ; test_ui_smoke::test_employee_sees_own_tickets_and_note_ac007 |
| AC-008 | test_service_update::test_update_status_changes_status_and_updated_at_ac013, test_updated_at_never_before_created_at; AC-013: test_service_update::test_update_status_changes_status_and_updated_at_ac013, test_transition_table_every_cell_ac013_ac014 |
| AC-009 | test_service_query::test_list_empty_and_all_ac009, test_list_newest_first; test_ui_smoke::test_engineer_view_and_updates_ac013_ac015 |
| AC-010 | test_service_query::test_filter_* ; test_ui_smoke::test_engineer_filter_no_match_shows_empty_state_ac010 |
| AC-011 | test_service_query::test_get_ticket_returns_all_fields_ac011; AC-012: test_service_query::test_get_unknown_id_not_found_ac012, test_get_invalid_id_validation_error, test_update_*_id_* |
| AC-012 | test_service_query::test_get_unknown_id_not_found_ac012, test_get_invalid_id_validation_error, test_update_invalid_id_rejected, test_update_unknown_id_not_found |
| AC-013 | test_service_update::test_update_status_changes_status_and_updated_at_ac013, test_transition_table_every_cell_ac013_ac014 |
| AC-014 | test_service_update::test_update_status_invalid_value_unchanged_ac014, test_transition_table_every_cell_ac013_ac014, test_closed_is_final_*, test_same_status_rejected |
| AC-015 | test_service_update::test_update_priority_ac015, test_update_priority_invalid_unchanged_ac015; AC-030: test_service_update::test_update_resolution_note_ac030, test_resolution_note_length_boundary_ac030, test_resolved_requires_note_ac030; test_ui_smoke::test_employee_sees_own_tickets_and_note_ac007 |
| AC-016 | test_dashboard::test_dashboard_empty_db_zero_filled_ac016; test_ui_smoke::test_manager_dashboard_empty_ac016 |
| AC-017 | test_dashboard::test_dashboard_status_counts_ac017_ac018; test_ui_smoke::test_manager_dashboard_counts_ac017 |
| AC-018 | test_dashboard::test_dashboard_status_counts_ac017_ac018 |
| AC-019 | test_dashboard::test_dashboard_by_priority_ac019 |
| AC-020 | test_dashboard::test_dashboard_reflects_changes_ac020 |
| AC-021 | test_persistence_security::test_persistence_across_connections_ac021, test_init_database_idempotent_keeps_data_ac021 |
| AC-022 | test_ui_smoke::test_role_selector_offers_three_roles_ac022, test_employee_create_ticket_flow_ac001, test_engineer_view_and_updates_ac013_ac015, test_manager_dashboard_empty_ac016 |
| AC-023 | test_architecture::test_readme_discloses_demo_selector_ac023; AC-031: test_ui_smoke::test_demo_banner_visible_for_every_role_ac031 |
| AC-024 | MANUAL (not automated) |
| AC-025 | test_persistence_security::test_sql_injection_stored_literally_ac025, test_injection_in_enum_fields_*; test_service_query::test_search_*_literal; test_architecture::test_repository_sql_is_static_no_fstring_sql |
| AC-026 | test_persistence_security::test_performance_1000_tickets_ac026 |
| AC-027 | test_architecture::test_app_has_no_sqlite3_or_repository_import_ac027, test_app_has_no_sql_strings_ac027 |
| AC-028 | test_ui_smoke::test_employee_create_ticket_flow_ac001 (partial; manual inspection: 4 form inputs + submit) |
| AC-029 | test_dashboard::test_dashboard_by_category_ac029 |
| AC-030 | test_service_update::test_update_resolution_note_ac030, test_resolution_note_length_boundary_ac030, test_resolved_requires_note_ac030; test_ui_smoke::test_employee_sees_own_tickets_and_note_ac007 |
| AC-031 | test_ui_smoke::test_demo_banner_visible_for_every_role_ac031 |
| AC-032 | `python -m ruff check .` command run: PASS (All checks passed!) after DEF-001 fix; evidence reports/ruff-output.txt |
| AC-033 | test_architecture::test_requirements_only_approved_deps_ac033, test_no_network_libraries_in_source_ac033 (review for rest) |

Status of AC-032: PASS (DEF-001 closed in cycle 1). AC-024: manual, not covered by pytest. All other ACs have at least one passing automated test.

## 9. Cycle 2: security-fix verification (F-02, F-03, F-05, F-06, F-10, F-11, F-12; AC-034..AC-037, NFR-013..NFR-017)
Date: 2026-10-24. New file: `tests/test_security_hardening.py` (180 cases). No production code, existing test or config was modified.

### Commands and actual results
- `python -m ruff check .` -> exit 0, `All checks passed!` (reports/ruff-output.txt). Two E501 in the new test file were fixed before the final run.
- `python -m pytest -v` (FULL suite) -> exit 1: **449 passed, 1 failed, 0 skipped in 15.08 s** (450 collected; previous 270 + 180 new). Evidence: reports/pytest-output.txt.
- `data/` directory was NOT created (`ls data` -> No such file or directory); the conftest session guard did not trigger.

### Failure (verbatim)
`FAILED tests/test_security_hardening.py::test_docs_state_demo_not_auth_and_no_public_deploy_ac037[README.md]` -> `assert "publicly deployed" in text` (README text has no such statement).

### Defects
| ID | Sev | Req | Description / evidence | Owner |
|---|---|---|---|---|
| DEF-002 | Low/Medium (documentation) | AC-037, NFR-009 | README.md "DEMO disclosure" says the selector is not authentication/authorization but never states the app must not be publicly deployed or exposed as a secure multi-user application. docs/architecture.md section 1 does state it (that parametrized case passes). Repro: `python -m pytest tests/test_security_hardening.py -k ac037`. Expected: README states it; actual: absent. Test left failing, not weakened. | backend-developer (owns README.md) |

### Fix verification
| Finding | Result | Tests |
|---|---|---|
| F-05 / NFR-013 / AC-035 | VERIFIED | 20 bad chars (NUL, C0, DEL, C1 U+0080/008D/009F, ZW U+200B-D/2060/FEFF, bidi U+202A-E/2066-9) x title/description/creator (60), resolution_note via update_resolution_note (20) and update_status (20), search (20), creator lookup (20): all raise ValidationError with the right field, nothing stored. Edge position (leading/trailing) rejected. Documented: leading/trailing U+0085 is stripped by str.strip as whitespace (accepted and trimmed), a middle U+0085 is rejected. \n \r \t allowed (as built: in every free-text field including title and search). Creator matching: ÉLISE/Élise/élise, NFC vs NFD, Straße vs STRASSE match; elise vs élise does not. |
| F-06 / NFR-014 / AC-034 | VERIFIED | search 100 ok / 101 rejected (field "search"), length after trim, case-insensitive substring over title+description, literal %, _, \, SQL-like text with table intact, combination with filters, empty result, UI empty-state (AppTest), UI text_input max_chars == SEARCH_MAX (AppTest + source check). |
| F-10 / NFR-015 | VERIFIED | /proc/x/y.db, path under a file, file used as directory -> DatabaseError with generic message not containing the path; UI shows generic error. New DB file 0o600 (also under umask 000), new data dir 0o700, existing file mode untouched. POSIX guard via skipif for non-POSIX only (ran, not skipped on this Linux host). |
| F-11 | VERIFIED | Connection proxy whose ROLLBACK raises sqlite3.OperationalError: original exception (custom Marker, and InvalidTransitionError via service) propagates; "Rollback failed" logged. |
| F-02 / F-03 / NFR-016 / NFR-017 / AC-036(b,c) | VERIFIED | config.toml parsed with tomllib: address 127.0.0.1, enableXsrfProtection true, enableCORS true, showErrorDetails "none", gatherUsageStats false. main.py broad except: AppTest shows generic "could not be opened" message, no exception element, internal message absent from page and from log records; logged via logging (caplog). |
| F-12 | VERIFIED | `plain()` escaping helper; AppTest: no markdown or caption element contains the raw typed name; it is shown via a plain st.text element. |
| AC-037 / NFR-009 | PARTIAL / FAIL | architecture.md passes; README.md fails (DEF-002). |

### AC coverage added
AC-034 (9 tests + existing search tests), AC-035 (see F-05), AC-036 a/b/c (see F-10, F-02/F-03/F-12), AC-037 (2 cases, 1 failing). AC-024 remains manual. Traceability rows for NFR-009, NFR-013..NFR-017 updated in docs/traceability.md.

### Status
Not all green: 1 open documentation defect (DEF-002). Retest required after the README fix.
