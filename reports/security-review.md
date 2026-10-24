# Security Review: IT Support Ticket Management System (local classroom MVP)

Reviewer: security-reviewer. Initial review: 2026-10-24. Fix verification (retest): 2026-10-24, performed by reading the current code and running probes myself; developer claims were not relied on.

## DEMO disclaimer (read first)
The role selector is NOT authentication or authorization. Anyone who can reach the app can pick any role, type any creator name, read every ticket (an Employee can read another person's tickets by typing their name), and call all engineer and manager functions. This version MUST NOT be publicly deployed, exposed on a network, or used as a secure multi-user application, and must not hold confidential data. This is NOT evidence of zero vulnerabilities and NOT a statement of production readiness.

## Retest results (verification of fixes)

### Commands re-run
| Command | Real result |
|---|---|
| `python -m ruff check .` | `All checks passed!` |
| `python -m pytest -q` | `450 passed in 15.04s` (also 16.07s on an earlier run; 36 tests in `tests/test_security_hardening.py`) |
| `pip-audit`, `bandit` | Still NOT installed; not run. No CVE or bandit scan exists. |
| `streamlit config show` (run from repo root) | `showErrorDetails = "none"`, `enableCORS = true`, `enableXsrfProtection = true`, `address = "127.0.0.1"` |
| Server started from repo root on port 8597, `ss -ltnp` | `LISTEN 127.0.0.1:8597` only; `/_stcore/health` returned 200; server stopped, no listener remained. |
| Server started from a DIFFERENT cwd (`/tmp`) on port 8596, `ss -ltn` | `LISTEN *:8596` (all interfaces). See new finding N-01. Server stopped (timeout), no listener remained. |
| Probe script on temp DBs (temp dirs only; no `data/` created in repo) | Details per finding below. |

### Per-finding verdicts
| ID | Verdict | Evidence |
|---|---|---|
| F-02 | Verified-Fixed (config part); catch-all not added | `.streamlit/config.toml` sets `showErrorDetails = "none"`, `enableXsrfProtection = true`, `enableCORS = true`, address 127.0.0.1; `streamlit config show` confirms effective values. `app/common.py:66-72` still catches only `TicketingError`/`NotImplementedError`; an unexpected exception is now hidden from the browser by Streamlit (not triggered in a browser by me). Residual: no generic catch-all with class-name logging in `call`. Config values only apply when Streamlit is started from the repo root (see N-01). |
| F-03 | Partially-fixed | `app/views_employee.py:27` now uses `st.text(...)`. `app/common.py:56-58` `plain()` escapes `\ ` * _ { } [ ] ( ) # + - . ! | > ~ $ < & :` in one regex pass, so backslash is not double-processed. Probe: `![x](http://h/p.png)` -> `\!\[x\]\(http\://h/p\.png\)`; `<b>x</b>` -> `\<b\>x\</b\>`; `$x$ :smile:` -> `\$x\$ \:smile\:`; `a\*b` -> `a\\\*b`. Correct for `st.error` (Markdown), applied at `common.py:69` and `main.py:45`. Still open: `app/views_engineer.py:35` selectbox `format_func` puts the raw ticket title in the option label; whether Streamlit renders Markdown there is not browser-tested. Suspected, Low. |
| F-05 | Partially-fixed | `ticketing/validation.py:204-216` now rejects C0, DEL, C1 (127-159), ZWSP/ZWNJ/ZWJ/WJ/BOM and the nine bidi embedding/override/isolate characters, applied to title, description, creator, note and search. Probe: U+202E, U+200B, U+200C, U+FEFF, U+0085, NUL rejected (creator U+202E rejected too). Not rejected (probe ACCEPTED): U+200E (LRM), U+00AD (soft hyphen), U+2028 (line separator), U+E0041 (tag character). Residual Low: these remaining invisible/format characters still allow look-alike names. Creator matching now uses the registered `UNICODE_NOCASE` collation (NFC + casefold): probe `Ärger`/`ÄRGER` matched 2 tickets via `ärger`; `école`/`ÉCOLE` matched 2. (My probe used the same NFC form for both sides, so NFC/NFD equivalence was not independently exercised.) Fix: reject Unicode category Cf (and Cc except \n\r\t) generally, plus U+2028/2029. |
| F-06 | Verified-Fixed | `ticketing/config.py:18` `SEARCH_MAX = 100`; `validation.py:320-321` enforces it; `views_list.py:155` `max_chars=SEARCH_MAX`. Probe: 100 chars ok; 101 and 50,000 chars -> `ValidationError: Search text must be 100 characters or fewer.` (no DB error, no log spam). LIKE literals still correct: `%` ->1 hit, `_` ->1, `' OR 1=1--` ->0, backslash ->0. |
| F-10 | Verified-Fixed | Probe on temp path `<tmp>/sub/t.db`: `dir mode 0o700 file mode 0o600` (`config.py:31` mkdir mode 0o700; `db.py:105-109` creates file 0600 via `os.open`). Bad paths `/proc/x/y.db`, `/dev/null/x/y.db`, `~nonexistentuser_zz/x.db` -> `DatabaseError` with message "A database error occurred. Please try again."; `str(e)` contains no path; cause chained (FileNotFoundError/NotADirectoryError/RuntimeError) but not displayed. A non-SQLite file as DB -> same generic `DatabaseError`. Residual (Info): `mkdir(mode=0o700)` only applies to the leaf directory when parents are created (intermediate dirs use umask), and pre-existing directories/files keep their existing modes; file creation permission is best effort (`except OSError: pass`). |
| F-11 | Verified-Fixed | `ticketing/db.py:148-153` wraps ROLLBACK in its own try/except. Probe: ROLLBACK forced to raise `OperationalError` -> the original `KeyError` still propagated and "Rollback failed" was logged; a normal `ValueError` inside a transaction propagated as `ValueError` and the INSERT was not persisted (row count unchanged). |
| F-12 | Partially-fixed (Info) | `app/main.py:43` now logs `type(exc).__name__` with `exc_info=True` and uses `common.plain`. Note `exc_info=True` writes a traceback (with paths) to the server log, not the browser; acceptable locally. Still present: broad `except Exception # noqa: BLE001`, function-local import (`main.py:41`), `sys.path` hack and `noqa: E402`. Maintainability only. |
| F-13 | Verified-Fixed | `docs/architecture.md:299-305` (section 14 deviations V-01, V-02, V-07) and `docs/implementation-plan.md:50` now document `app/main.py`, `app/views_*.py`, `python -m streamlit run app/main.py`. A grep for `app.py`, `ui/`, `stub_service` now hits only the deviation table (`architecture.md:299-305`) and `implementation-plan.md:50`, which explain the change; no stale layout descriptions remain. |
| DEF-002 (README disclosure) | Verified-Fixed | `README.md` lines 6-17 state the role selector is NOT authentication/authorization, names are unverified, anyone can view/change any ticket, no deployment, no confidential data, bound to 127.0.0.1, and document the search cap, rejected characters and 0600 file mode. UI banner `app/common.py:17-20` is consistent. Caveat: the 127.0.0.1 statement is only true when started from the repo root (N-01). |

### Regression checks on the fixes
- UNICODE_NOCASE collation: registered per connection in `db.py:111`; the only use is the static constant `creator COLLATE UNICODE_NOCASE = ?` in `repository.py:30`. The collation name is a literal, not built from input; no SQL string-building anywhere (`repository.py` all `?`-parameterized, grep re-checked). The collation function is pure and cannot raise on `str` input.
- Performance with 1,000 tickets (temp DB): create 1,000 = 0.97 s; list all 1,000 = 0.011 s; search = 0.002 s; creator lookup = 0.002 s. Index `idx_tickets_creator_nocase` uses the built-in NOCASE collation, so the UNICODE_NOCASE comparison does a full scan (`EXPLAIN QUERY PLAN: SCAN tickets`); irrelevant at this scale, would matter at large scale (Info).
- `plain()` correctness: single `re.sub` pass, so the backslash is escaped once and never re-escaped; output is only used for Markdown sinks (`st.error`). Not used on `st.text`, so no stray backslashes shown there.
- Rollback handling and error mapping: no masking regression (see F-11).
- `views_employee._my_tickets` still filters search in Python (`views_employee.py:127-129`) using `str.lower()` rather than the SQL path; harmless, and the search cap is enforced by the widget `max_chars`.

## New findings from retest
| ID | Severity | Location | Description | Evidence | Fix | Status |
|---|---|---|---|---|---|---|
| N-01 | Medium (confirmed) for anyone who ignores the README; Low for the documented run | `.streamlit/config.toml` (project-relative), README Run section | Streamlit only loads `.streamlit/config.toml` from the current working directory (and `~/.streamlit`). Starting `python -m streamlit run /path/to/app/main.py` from another directory loses the 127.0.0.1 binding and showErrorDetails="none". Probe: from `/tmp`, `ss -ltn` showed `LISTEN *:8596` (all interfaces). From the repo root: `127.0.0.1:8597`. With no auth, that exposes every ticket to the LAN. | Probe outputs above. | Pass `--server.address 127.0.0.1` in the documented run command (README) and/or add a startup guard that refuses to run if `server.address` is not loopback; explicitly state "run from the repo root". Owner: frontend-developer / orchestrator for README. | Open |
| N-02 | Low (confirmed) | `ticketing/validation.py:204-216` | Residual invisible/format characters accepted (U+200E, U+00AD, U+2028, U+E0041); see F-05. | Probe. | See F-05. | Open |
| N-03 | Info (suspected) | `app/views_engineer.py:35` | Selectbox label contains raw title; Markdown rendering unconfirmed. See F-03. | Code read. | Pass title through `common.plain` in `format_func`. | Open |

## Final status of all original findings
| ID | Severity | Final status |
|---|---|---|
| F-01 | High if exposed beyond local use | Accepted documented limitation for the local demo only; NOT fixed; High if the app is reachable by others (and N-01 shows it can become so). |
| F-02 | Medium | Verified-Fixed (config); catch-all residual |
| F-03 | Low | Partially-fixed |
| F-04 | Low | Open (CSV/formula injection via dataframe export; `toolbarMode` not set, `ticket_rows` unchanged; not browser-tested) |
| F-05 | Low | Partially-fixed |
| F-06 | Low | Verified-Fixed |
| F-07 | Low | Open, accepted for classroom scale (1,000 tickets list in 11 ms) |
| F-08 | Low | Open, awaiting human product decision (Closed tickets still allow priority/note edits; code unchanged) |
| F-09 | Low | Open, accepted for demo (last-write-wins) |
| F-10 | Low | Verified-Fixed |
| F-11 | Info | Verified-Fixed |
| F-12 | Info | Partially-fixed |
| F-13 | Info | Verified-Fixed |
| F-14 | Info | Open, deferred (unpinned deps, no pip-audit) |
| F-15 | Info | Open, deferred (maintainability) |
| DEF-002 | README disclosure | Verified-Fixed |
| N-01 | Medium | New, Open |
| N-02 | Low | New, Open |
| N-03 | Info | New, Open (suspected) |

### Severity summary (open or partially-fixed items only, after retest)
| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | none |
| High | 1 (conditional) | F-01 (accepted demo limitation; High only if exposed) |
| Medium | 1 | N-01 |
| Low | 7 | F-03 (partial), F-04, F-05 (partial)/N-02, F-07, F-08, F-09 |
| Info | 5 | F-02 residual, F-12, F-14, F-15, N-03 |
Verified-Fixed: F-02 (config), F-06, F-10, F-11, F-13, DEF-002.

Sign-off gate in CLAUDE.md: no unaccepted High/Critical finding exists inside the stated local scope; F-01 is accepted by design and must be explicitly accepted by the human. N-01 should be fixed (or the README command changed) before anyone runs it off a shared network.

## Residual risk
Any local user or LAN host that can reach the port can read and modify all data (F-01, aggravated by N-01 if started from the wrong directory). Spreadsheet formula injection via export (F-04), look-alike names via the remaining invisible characters (N-02), unbounded lists and lost-update behaviour (F-07, F-09), and editable closed tickets (F-08, pending decision) remain. Dependencies are unaudited (F-14).

## Limits of this review
- Static read plus service-layer probes and local server start/stop; no browser rendering tests (F-03, F-04, N-03 behaviours are unconfirmed in a browser).
- `pip-audit` and `bandit` are not installed; no dependency CVE scan or bandit run was done. Only ruff (incl. `S` rules) passed.
- No fuzzing, load testing beyond 1,000 rows, OS hardening or Streamlit internals review.
- Passing 450 tests and a clean ruff run do not prove absence of vulnerabilities. This review is NOT evidence of zero vulnerabilities and NOT evidence of production readiness.

---
# Original review (initial pass, retained for history; status column superseded by the tables above)

## Findings
Severity scale: Critical/High/Medium/Low/Info. "Confirmed" = reproduced or read directly in code; "Suspected" = needs verification. No Critical or High findings were identified within the stated scope, other than the documented DEMO limitation (F-01), which is rated for deployment context.

| ID | Severity | Location | Description | Evidence | Recommended fix | Owner | Status |
|---|---|---|---|---|---|---|---|
| F-01 | High if deployed beyond local use; Accepted documented limitation for the local classroom MVP | `app/main.py:29-33,47-52`, `ticketing/service.py` (no caller identity), `app/common.py:16` | No authentication/authorization. Role and creator name are client-chosen; engineer/manager functions reachable by anyone; employees can read others' tickets by typing the name; creator "ownership" is only a case-insensitive name match. Confirmed. | Code read; `list_tickets_for_creator` takes a free-text name. | Accept for local demo (banner + README disclose it). Before any shared use: real authentication, server-side role checks in the service layer, per-user ownership. Do not deploy publicly. | frontend-developer (UI) / solution-architect (design) | Accepted risk (demo only) |
| F-02 | Medium | `.streamlit/config.toml` | Config only sets address and usage stats. `client.showErrorDetails` stays default "full" in Streamlit 1.66.1, so any unexpected non-`TicketingError` exception (e.g. `OSError` from `mkdir`/file permissions in views, or bug) can render a Python traceback with file paths in the browser. `common.call` and `main.py` only catch `TicketingError` / broad errors at DB bootstrap, not other exceptions in views. Confirmed config gap; traceback display itself Suspected (not triggered). | `streamlit config show`: `showErrorDetails = "full"` default; `app/common.py:55-66`. | Add `[client] showErrorDetails = "none"` (or "stacktrace" avoided) and optionally `toolbarMode = "minimal"`; consider a catch-all in `common.call` that logs the class name and shows a generic message. Also set `[server] enableXsrfProtection = true`, `enableCORS = true` explicitly so a future override cannot silently weaken them, and `port`. | frontend-developer | Open |
| F-03 | Low | `app/views_employee.py:26`, `app/main.py:33` | `st.caption(f"Creating as: {requester}")` renders user-typed text as Markdown (caption supports markdown). A name such as `![x](http://host/p.png)` or a link would render an external image/link (tracking-pixel/phishing-style content, self-inflicted in own session). HTML is not enabled. Confirmed by code; not browser-tested. | `st.caption` markdown semantics; name is free text up to 100 chars. | Use `st.text(...)` or escape markdown characters. Also check selectbox `format_func` labels containing ticket titles (`views_engineer.py:35`) render as plain text (Suspected; Streamlit may apply limited markdown to option labels). | frontend-developer | Open |
| F-04 | Low | `app/common.py:87-93`, `app/views_engineer.py:35` | Titles, descriptions and creators are stored verbatim and displayed in `st.dataframe`, whose toolbar offers CSV download. Values beginning with `=`, `+`, `-`, `@` (probe stored creator `=HYPERLINK("http://e")`) are CSV/formula-injection candidates when the export is opened in a spreadsheet. Confirmed storage; export behaviour Suspected. | Probe created ticket with creator `=HYPERLINK(...)`: accepted. | Set `[client] toolbarMode = "minimal"` or `column_config`; or prefix `'` to cells starting with formula characters in `ticket_rows`; optionally restrict leading `=+-@` in creator/title. | frontend-developer | Open |
| F-05 | Low | `ticketing/validation.py:23-33` | Control-character filter allows only `\n \r \t` and < 32/127; it does not reject Unicode C1 controls (U+0085), zero-width (U+200B) or bidi overrides (U+202E). Probe: all three accepted in title; NUL rejected. Enables spoofed/invisible text and look-alike creator names (also `COLLATE NOCASE` is ASCII-only, so `Ä`/`ä` differ). Confirmed. | Probe output: `'a‮b' accepted`, `'a​b' accepted`, `'\x85x' accepted`, `'a\x00b' rejected`. | Reject Unicode category Cc (except `\n\r\t`) and Cf for single-line fields (title, creator); NFC-normalize creator before storing/matching. | backend-developer | Open |
| F-06 | Low | `ticketing/validation.py:118-125`, `app/views_list.py:22` | Search term has no length cap in service or UI. Probe: 5,000 chars OK; 50,000 chars raises `sqlite3.OperationalError: LIKE or GLOB pattern too complex` which is mapped to the generic `DatabaseError` (handled, no leak, but logs an error and offers a trivial request-level DoS/log spam). Confirmed. | Probe as above. | Add `SEARCH_MAX` (e.g. 100) in `config.py`, enforce in `validate_search`, and `max_chars` on the search input. | backend-developer (limit), frontend-developer (`max_chars`) | Open |
| F-07 | Low | `ticketing/repository.py:24-33`, `service.py:106-128`, `app/common.py:87-93`, `views_employee.py:56-68` | No pagination or LIMIT: every list call loads all matching rows (including 2,000-char descriptions) into memory and the browser; "My tickets" filters in Python after loading all of a creator's tickets; the engineer detail dropdown loads all tickets on every rerun. DoS/perf risk only grows with unbounded ticket creation (no rate limit/quota). Confirmed by code (not load-tested here; QA reports a 1,000-ticket timing test). | Code read. | Add `limit/offset` to `query_tickets`/`list_tickets` and a page size in the UI; push filters for "My tickets" into SQL; accept for classroom scale and document. | backend-developer / frontend-developer | Open (accepted for classroom scale) |
| F-08 | Low | `ticketing/service.py:188-206`, `app/views_engineer.py:99-109` | Data integrity scope: resolution note (and priority, `service.py:169-185`) remain editable on Closed tickets, so "Closed-final" covers status only. Probe: after Resolved->Closed, `update_priority` and `update_resolution_note("changed after close")` succeeded and bumped `updated_at`. Matches FR-021 as written, but weakens the audit value of closed tickets; there is no change history or actor record. Confirmed. | Probe output: `Priority.LOW changed after close`. | Product decision: either document explicitly (README/requirements) that Closed freezes status only, or reject priority/note edits when status is Closed. Without auth, an audit trail has little value anyway. | solution-architect (decision), backend-developer | Open (needs decision) |
| F-09 | Low | `ticketing/service.py:147-166` | Concurrency: updates are last-write-wins with no version/updated_at check. The status transition itself is safe (read, validate, write inside one `BEGIN IMMEDIATE`), but a form rendered earlier can overwrite a newer priority/note silently (e.g. the status form re-submits the note shown at render time, `views_engineer.py:73-79`). Confirmed by code. | Code read. | Optional optimistic locking: pass the expected `updated_at` and reject on mismatch. | backend-developer | Open (accepted for demo) |
| F-10 | Low | `ticketing/config.py:18-26`, `app/common.py:31-35` | `TICKETS_DB_PATH` is taken verbatim (`expanduser`), the parent directory is created with `mkdir(parents=True)` default mode (probe: dir 0775), and the DB file is created with umask-derived 0644 (probe), i.e. group/world readable on a shared machine. No path-traversal issue since the path comes from the operator's environment, not from users; failure to create it surfaces as an uncaught `FileNotFoundError`/`OSError` from `get_db_path` (probe with `/proc/x/y.db`). In `main.py` this is inside the broad `try`, so it is shown as a generic message; other callers are not guarded. Confirmed. | Probe: `db 0o644 dir 0o775`; `FileNotFoundError` for an invalid path. | Create `data/` with mode 0700 and chmod the DB 0600 after creation (or set `os.umask(0o077)` before connect); wrap `OSError` in `get_db_path` as `DatabaseError`; document that the env var is trusted. | backend-developer | Open |
| F-11 | Info | `ticketing/db.py:95-98` | `except BaseException: ROLLBACK` can itself raise `sqlite3.Error` and mask the original exception; `COMMIT` failure (e.g. SQLITE_BUSY) is converted to `DatabaseError` but the connection is closed without explicit rollback (SQLite rolls back on close, acceptable). Foreign keys PRAGMA is unused (no FKs). | Code read. | Wrap the rollback in its own try/except. | backend-developer | Open |
| F-12 | Info | `app/main.py:35-46` | Broad `except Exception  # noqa: BLE001` and a function-local import; fine for safe messages but swallows the cause with no logging of the exception class. Also `sys.path` bootstrap hack and many `# noqa: E402`. Maintainability only. | Code read. | Log `type(exc).__name__`; import `TicketingError` at top. | frontend-developer | Open |
| F-13 | Info | `docs/architecture.md:16,31,39-40,168,187,219,228,260`, `docs/implementation-plan.md:19-24,41-43` | Doc drift: documents describe `app.py`, `ui/**`, `ui/stub_service.py`, `streamlit run app.py`; the code uses `app/main.py`, `app/views_*.py`, `app/common.py`, run via `python -m streamlit run app/main.py`. `test_architecture` scan target in the doc (`ui/`, `app.py`) is stale. | grep output. | Update docs to the real layout. | solution-architect | Open |
| F-14 | Info | `requirements.txt` | Dependencies unpinned (`streamlit>=1.30`, `pytest>=7.4`, `ruff>=0.4`); dev tools mixed with runtime requirements; no lock file; no CVE audit possible (pip-audit absent). | File content; `pip check` clean. | Pin/lock versions, split `requirements-dev.txt`, run `pip-audit` after human approval to install it. | qa-engineer (pyproject/tooling) / backend-developer | Open |
| F-15 | Info | `app/views_engineer.py:46-59`, `views_employee.py:60-68`, `ticketing/repository.py:57-73` | Maintainability: "My tickets" duplicates filtering logic that the service already provides (`TicketFilter`); `list_tickets_for_creator` cannot take filters; `ticket_rows` and `_show_details` duplicate field formatting; `models.py` and `UNSET` sentinel add small complexity. Ruff reports no problems. | Code read. | Optionally let `list_tickets_for_creator` accept a `TicketFilter`. | backend-developer | Open |

## Accepted risks
| Risk | Classification | Rationale / condition |
|---|---|---|
| F-01 DEMO role selector, unverified names, any user can read/modify any ticket | Documented limitation; High severity if exposed, accepted for a single-user local classroom run | Disclosed in README and persistent UI banner; server bound to 127.0.0.1. Valid only while the app runs locally and holds no confidential data. |
| F-07 unbounded lists, F-09 last-write-wins | Accepted for classroom scale | Revisit before multi-user use. |

## Binding and transport
`.streamlit/config.toml` sets `server.address = "127.0.0.1"` (confirmed listening on loopback only). XSRF and CORS protections are at Streamlit defaults (enabled) and are not pinned in config. There is no TLS and no auth; any local user on the same machine can reach the port. Running with `--server.address 0.0.0.0` or behind a tunnel would expose all data.

## Limitations of this review
- Static read plus targeted service-layer probes; no browser-based testing of Streamlit rendering (F-03/F-04 behaviours are unconfirmed in the browser).
- No dependency vulnerability scan (pip-audit absent) and no bandit run; ruff's `S` rules passed.
- No load/performance testing, no fuzzing, no review of Streamlit internals, OS-level hardening, or deployment settings.
- Nothing here is evidence of "no vulnerabilities" or production readiness; no fixes were verified because none have been made yet. All findings remain Open until re-tested by the owning agent and re-checked by the reviewer.
