# Requirements: IT Support Ticket Management System (Local Classroom MVP)

Status: REVISED (v3) to match the human-approved scope and the as-built system (`docs/architecture.md` section 14, V-01..V-08; decisions D-01..D-04 approved with the architecture). Items still marked OPEN / ASSUMPTION need human approval.
v3 changes: search in scope (FR-006, AC-034); A-02, A-16, A-18 closed as Approved/implemented; security-hardening NFR-013..NFR-017 added; NFR-009 extended; new open item A-19.
Source: `docs/client-requirements.md` (verbatim client text) plus the human-approved scope below.
Change markers: [CHANGED], [ADDED], [REMOVED]. IDs are kept stable; no ID has been reused for a different meaning except where marked [CHANGED].

## 0. Human-approved scope (v2)
- Python 3.10+; Streamlit UI; SQLite via built-in `sqlite3`; pytest for tests; Ruff for linting.
- Employee, Support Engineer and Manager views.
- Employee can create tickets and view ticket status.
- Engineer can inspect tickets, change priority/status and add resolution notes.
- Manager dashboard: total, open, in-progress, resolved and closed counts, plus priority and category breakdowns.
- Ticket fields: ID, title, description, category, priority, status, creator, created_at, updated_at, resolution_note.
- Status values: Open, In Progress, Resolved, Closed. Priority values: Low, Medium, High, Critical.
- Tickets persist in a local SQLite database.
- A clearly labeled DEMO role selector, NOT real authentication and NOT secure authorization; must be disclosed in documentation.
- No cloud services, external APIs or deployment.

## 1. Scope summary
A local web-based demo where employees raise tickets and view their status, support engineers inspect and update tickets (priority, status, resolution note), and managers see a dashboard of counts. Data persists in local SQLite. Access is via a DEMO role selector only.

## 2. Out of scope
- Login/authentication, passwords, SSO, registration, real access control. The DEMO selector is not security (A-01 Approved).
- Email/SMS notifications, SLA timers, escalation rules.
- File attachments, screenshots.
- [CHANGED] Ticket deletion, comments/history log, and assignment to a specific engineer are not in the approved scope (A-08 resolved by omission; assignee removed from A-06). Tell me if any is wanted.
- Bulk import/export, reporting beyond the dashboard, CSV export. [CHANGED v3] Ticket text search is now IN SCOPE (FR-006, AC-034); it was removed from this list at the human's explicit request for "a ticket listing page with search and filters".
- Multi-tenant, internationalisation, mobile apps.
- Cloud services, external APIs, deployment, publishing, integrations.
- Audit-grade history, encryption at rest, backups (A-14 open).

## 3. Functional requirements

| ID | Requirement | Source / change |
|---|---|---|
| FR-001 | An employee can create a ticket by supplying a title, a description and a category. | [CHANGED] category added (approved fields) |
| FR-002 | A ticket carries a priority from the fixed list Low, Medium, High, Critical. Whether the employee sets it at creation is OPEN (A-05); if not set, default is Medium (A-17). | [CHANGED] values Approved |
| FR-003 | The system rejects ticket creation when required fields are missing, blank, or exceed length limits (A-06), or when category is not one of Hardware, Software, Network, Access, Other (A-18 Approved), showing a clear message. | [CHANGED v3] |
| FR-004 | Each ticket gets a unique ID, a created_at and updated_at timestamp, and is created with status "Open" (A-17). | [CHANGED] |
| FR-005 | An employee can view the status of tickets they created. "Their" = tickets whose creator equals the name typed in the sidebar, by case-insensitive, Unicode-aware exact match (A-02 Approved, D-03); the name is unverified. | [CHANGED v3] |
| FR-006 | A support engineer can view a list of all tickets, filterable by status and priority (and category, as built), and searchable by text: a case-insensitive substring match over title and description, search text at most 100 characters, matched literally (no wildcard or SQL meaning). Search combines with the filters. | [CHANGED v3] search in scope per human instruction (V-03); category filter as built |
| FR-007 | A support engineer can view the full details of a single ticket, including all approved fields. | [CHANGED] |
| FR-008 | A support engineer can change a ticket's status to one of Open, In Progress, Resolved, Closed. Whether transitions are restricted is OPEN (A-03). | [CHANGED] |
| FR-009 | A support engineer can change a ticket's priority to one of the allowed values. | [CHANGED] now Approved (no longer assumption) |
| FR-010 | The system rejects any status value outside the four allowed values and leaves the ticket unchanged. If transitions are restricted (A-03 decision), it also rejects disallowed transitions. | [CHANGED] |
| FR-011 | The system updates updated_at on every change to a ticket. | unchanged |
| FR-012 | The dashboard shows the total number of tickets. | unchanged |
| FR-013 | The dashboard shows the number of Open tickets and the number of In Progress tickets, separately. | [CHANGED] replaces "pending" (A-07 superseded) |
| FR-014 | The dashboard shows the number of Resolved tickets and the number of Closed tickets, separately. | [CHANGED] replaces combined "resolved" |
| FR-015 | The dashboard shows ticket counts per priority level (all four levels, including 0). | unchanged |
| FR-016 | Dashboard figures reflect current stored data on each load/refresh. | unchanged |
| FR-017 | All ticket data is stored in a local SQLite database and survives application restart. | unchanged |
| FR-018 | The user selects a role (Employee, Support Engineer, Manager) via a DEMO selector and is shown the screens for that role. This is a UI convenience, NOT access control. | [CHANGED] |
| FR-019 | The application is accessed through a web browser (Streamlit). | unchanged |
| FR-020 | The dashboard shows ticket counts per category (all five fixed categories, including 0; counts sum to total). | [ADDED] [CHANGED v3] |
| FR-021 | A support engineer can add or edit a resolution_note on a ticket. A non-blank note is required to move a ticket to Resolved; Closed keeps the note (A-16 Approved, D-04). The note is visible to the employee who created the ticket. Whether priority/resolution note may be edited on Closed tickets is OPEN (A-19; currently allowed). | [ADDED] [CHANGED v3] |
| FR-022 | The UI shows a clearly visible "DEMO" label by the role selector stating it is not authentication or secure authorization. | [ADDED] |

## 4. Non-functional requirements

| ID | Requirement | Notes |
|---|---|---|
| NFR-001 | Usability: a first-time user can create a ticket with one form of no more than 5 inputs and no training. | [CHANGED] form inputs: title, description, category, creator (A-02), plus optional priority (A-05); still within 5. Needs approval (A-12) |
| NFR-002 | Validation and error messages are plain-language and identify the offending field. | unchanged |
| NFR-003 | Persistence: committed data is retained across restarts; nothing stored only in memory/session. | unchanged |
| NFR-004 | Data integrity: all SQL parameterized; status and priority restricted to allowed values at the data layer. | unchanged |
| NFR-005 | Performance (MVP): list and dashboard respond in under 2 seconds with up to 1,000 tickets on a typical laptop. | ASSUMPTION A-10, still open |
| NFR-006 | Compatibility: current Chrome and Firefox. | ASSUMPTION A-11, still open |
| NFR-007 | UI layer contains no SQL; it uses the service layer only. | unchanged |
| NFR-008 | Every acceptance criterion has at least one automated pytest test (except those marked manual/review). | unchanged |
| NFR-009 | Security LIMITATION, not a guarantee: the role selector is a DEMO and is not authentication or secure authorization. Any user can choose any role and view or alter any data. No confidentiality or integrity guarantee is made. This must be disclosed in project documentation (README/docs) and in the UI (FR-022). The application must not be publicly deployed or exposed as a secure multi-user application. | [CHANGED] disclosure now mandatory; Q-01 resolved; v3 adds the no-public-deployment statement |
| NFR-010 | Deployment: runs locally on one machine; no cloud services, no external APIs, no deployment. | [CHANGED] extended |
| NFR-011 | Technology: Python 3.10+; Streamlit; built-in `sqlite3`; pytest. No other runtime dependencies without human approval. | [ADDED] |
| NFR-012 | Code quality: the codebase passes Ruff linting with the project's Ruff configuration. | [ADDED] |
| NFR-013 | Input hygiene: free-text fields (title, description, creator, category/other text, resolution note, search text) are rejected if they contain control characters, zero-width characters or bidirectional-override characters. Ordinary newlines/tabs handling in multi-line fields follows the implemented validator. This is input hygiene, not a security guarantee. | [ADDED v3] as built (V-03/F-series hardening) |
| NFR-014 | Search text is limited to 100 characters; longer input is rejected with a clear message. | [ADDED v3] |
| NFR-015 | The SQLite database file is created with owner-only permissions on a best-effort basis (may not be effective on all platforms/filesystems). No confidentiality guarantee is made. | [ADDED v3] |
| NFR-016 | The app binds to localhost (127.0.0.1) only by default configuration (`.streamlit/config.toml`) and usage statistics are disabled. Changing the binding is unsupported (see NFR-009). | [ADDED v3] (V-04) |
| NFR-017 | The browser never shows Python tracebacks or internal error details; unexpected errors show a generic message. | [ADDED v3] |

## 5. User stories

### Employee
- US-001: As an employee, I want to raise a ticket with title, description and category, so that IT knows my issue. (FR-001, FR-003, FR-004, NFR-001, NFR-002) [CHANGED]
- US-002: As an employee, I want ticket priority to be recorded (Low/Medium/High/Critical), so that urgency is communicated. (FR-002) [CHANGED: who sets it at creation is OPEN, A-05]
- US-003: As an employee, I want to see the current status of my tickets (and any resolution note), so that I can track progress. (FR-005, FR-011, FR-021) [CHANGED]

### Support engineer
- US-004: As a support engineer, I want to see all tickets, filter by status and priority, and search by text, so that I can find tickets quickly. (FR-006) [CHANGED v3: search]
- US-005: As a support engineer, I want to open a ticket and see its full details. (FR-007)
- US-006: As a support engineer, I want to update a ticket's status. (FR-008, FR-010, FR-011)
- US-007: As a support engineer, I want to adjust a ticket's priority. (FR-009, FR-011) [CHANGED: Approved]
- US-012: As a support engineer, I want to add a resolution note to a ticket, so that the employee and others know how it was resolved. (FR-021, FR-011) [ADDED]

### Manager
- US-008: As a manager, I want to see total, open, in-progress, resolved and closed counts, so that I understand workload. (FR-012, FR-013, FR-014, FR-016) [CHANGED]
- US-009: As a manager, I want to see ticket counts by priority and by category, so that I can see where the backlog is. (FR-015, FR-020, FR-016) [CHANGED]

### Cross-cutting
- US-010: As any user, I want my tickets to still exist after restart. (FR-017, NFR-003)
- US-011: As any user, I want to open the system in a browser and pick a DEMO role, understanding it is not secure. (FR-018, FR-019, FR-022, NFR-006, NFR-009) [CHANGED]

## 6. Acceptance criteria (Given/When/Then)

- AC-001 (US-001; FR-001, FR-004) [CHANGED]: Given valid title, description and category, when an employee submits the form, then a ticket is stored with a unique ID, status "Open", created_at and updated_at set, and the ID is shown.
- AC-002 (US-001; FR-003, NFR-002): Given an empty or whitespace-only title or description (or creator, if required per A-02), when submitted, then no ticket is created and an error naming the field is shown.
- AC-003 (US-001; FR-003): Given a title over 100 characters or a description over 2000 characters (A-06), when submitted, then it is rejected and no ticket is created.
- AC-004 (US-002; FR-002): Given a priority from the allowed list, when a ticket is created with it, then the stored priority equals the one chosen. If none is supplied, the default (A-17) is stored. [CHANGED]
- AC-005 (US-002; FR-002, NFR-004): Given a priority not in {Low, Medium, High, Critical}, when creation is attempted, then it is rejected and no ticket is created.
- AC-006 (US-001; FR-004): Given two tickets created in sequence, their IDs differ.
- AC-007 (US-003; FR-005): Given tickets created by employee X and employee Y, when X views their tickets, then only X's tickets appear with current status. (Matching rule depends on A-02.)
- AC-008 (US-003; FR-011): Given a ticket updated by an engineer, when the employee views it, then the new status and updated_at are shown.
- AC-009 (US-004; FR-006): Given N stored tickets, the engineer list shows all N.
- AC-010 (US-004; FR-006): Given mixed tickets, filtering by status and/or priority shows only matches; no match shows an empty-state message.
- AC-011 (US-005; FR-007) [CHANGED]: Given an existing ticket ID, when an engineer opens it, then ID, title, description, category, priority, status, creator, created_at, updated_at and resolution_note (or empty) are shown.
- AC-012 (US-005; FR-007): Given a non-existent ticket ID, a "not found" result is returned without crash.
- AC-013 (US-006; FR-008, FR-011) [CHANGED]: Given a ticket and a permitted new status (any of the four if unrestricted; an allowed transition if restricted, A-03), when the engineer sets it, then it is stored and updated_at changes.
- AC-014 (US-006; FR-010) [CHANGED]: Given a status value outside the four allowed values, when attempted, then it is rejected, an error is shown, and the ticket is unchanged. If A-03 restricts transitions, a disallowed transition is rejected the same way. (Transition part PENDING A-03.)
- AC-015 (US-007; FR-009, FR-011): Given a valid new priority, when an engineer changes it, then it is stored and updated_at changes; an invalid priority is rejected with no change.
- AC-016 (US-008; FR-012, FR-016): Given N tickets, the dashboard total equals N; with zero tickets it shows 0.
- AC-017 (US-008; FR-013) [CHANGED]: Given tickets in various statuses, the dashboard Open count equals the number with status Open and the In Progress count equals the number with status In Progress.
- AC-018 (US-008; FR-014) [CHANGED]: Given tickets in various statuses, the dashboard Resolved count and Closed count each equal the number of tickets with that status; the four status counts sum to the total.
- AC-019 (US-009; FR-015): Given mixed priorities, the dashboard shows a count for each priority level (including 0) and the counts sum to the total.
- AC-020 (US-008, US-009; FR-016): Given a ticket is created or its status/priority/category data changes, when the dashboard is reloaded, then the figures reflect it.
- AC-021 (US-010; FR-017, NFR-003): Given saved tickets, when the DB connection is closed and reopened, the same tickets and field values (including resolution_note) are retrievable.
- AC-022 (US-011; FR-018) [CHANGED]: Given a selected role, the screens offered match the mapping (Employee: create ticket and view status; Engineer: list/detail/update priority, status, resolution note; Manager: dashboard).
- AC-023 (US-011; NFR-009) [CHANGED]: The project documentation (README/docs) states that the role selector is a DEMO, not authentication, and not secure authorization. Verification: documented text present; no security behaviour is asserted.
- AC-024 (US-011; FR-019, NFR-006): Given the app is started locally, the main page loads in current Chrome or Firefox. (Manual, not pytest.)
- AC-025 (NFR-004): Given input such as `'; DROP TABLE tickets;--` in text fields, it is stored as literal text and the table remains intact.
- AC-026 (NFR-005): Given 1,000 tickets, list and dashboard each load within 2 seconds (A-10).
- AC-027 (NFR-007): Static check: UI modules contain no SQL and no `sqlite3` import.
- AC-028 (NFR-001): The ticket creation form has no more than 5 inputs. (Manual/UI inspection.)
- AC-029 (US-009; FR-020) [ADDED]: Given tickets in mixed categories, the dashboard shows a count per category and the counts sum to the total.
- AC-030 (US-012; FR-021, FR-011) [ADDED]: Given an engineer saves a resolution note on a ticket, then it is stored, updated_at changes, and the creating employee sees it. A note exceeding the length limit (A-06) is rejected. If A-16 requires a note, setting Resolved/Closed without one is rejected with no change. (A-16 part PENDING.)
- AC-031 (US-011; FR-022, NFR-009) [ADDED]: Given any role is selected, the UI shows a visible DEMO label stating the selector is not authentication or secure authorization. (UI inspection; automated if feasible.)
- AC-032 (NFR-012) [ADDED]: Running Ruff over the codebase reports no violations. (Command-run check with output as evidence.)
- AC-033 (NFR-011, NFR-010) [ADDED]: The project runs on Python 3.10+ using only Streamlit, built-in `sqlite3`, pytest and Ruff, and makes no network/external API calls. (Review of dependency list and code; verified by review.)
- AC-034 (US-004; FR-006, NFR-004, NFR-014) [ADDED v3]: Given tickets with varied titles/descriptions, when the engineer searches text T (at most 100 chars), then only tickets whose title or description contains T, case-insensitively, are listed; `%`, `_` and `\` in T match literally; SQL-like text such as `'; DROP TABLE tickets;--` is treated as plain text and the table remains intact; search combines with status/priority/category filters; no match shows the empty-state message; text over 100 characters is rejected with an error and no search runs. (QA: map existing search tests, e.g. test_service_query::test_search_*, here.)
- AC-035 (NFR-013) [ADDED v3]: Given free text containing control, zero-width or bidi-override characters, when submitted (create, note update, creator name, search), then it is rejected naming the field and nothing is stored.
- AC-036 (NFR-015, NFR-016, NFR-017) [ADDED v3]: (a) On a POSIX filesystem the created DB file mode has no group/other permission bits (best effort); (b) `.streamlit/config.toml` sets `server.address` to 127.0.0.1; (c) when an unexpected exception occurs in the service/UI, the rendered page shows a generic message and no traceback. (Automated where feasible; (b) by config inspection.)
- AC-037 (NFR-009) [ADDED v3]: Project documentation states the app must not be publicly deployed or exposed as a secure multi-user application. (Documentation inspection.)

## 7. Requirement to acceptance-criteria mapping

| US | FR / NFR | AC |
|---|---|---|
| US-001 | FR-001, FR-003, FR-004, NFR-001, NFR-002 | AC-001, AC-002, AC-003, AC-006, AC-028 |
| US-002 | FR-002 | AC-004, AC-005 |
| US-003 | FR-005, FR-011, FR-021 | AC-007, AC-008, AC-030 |
| US-004 | FR-006, NFR-014 | AC-009, AC-010, AC-034 |
| US-005 | FR-007 | AC-011, AC-012 |
| US-006 | FR-008, FR-010, FR-011 | AC-013, AC-014 |
| US-007 | FR-009, FR-011 | AC-015 |
| US-012 | FR-021, FR-011 | AC-030 |
| US-008 | FR-012, FR-013, FR-014, FR-016 | AC-016, AC-017, AC-018, AC-020 |
| US-009 | FR-015, FR-020, FR-016 | AC-019, AC-029, AC-020 |
| US-010 | FR-017, NFR-003 | AC-021 |
| US-011 | FR-018, FR-019, FR-022, NFR-006, NFR-009 | AC-022, AC-023, AC-024, AC-031, AC-037 |
| (technical) | NFR-004, NFR-005, NFR-007, NFR-008, NFR-010, NFR-011, NFR-012 | AC-025, AC-026, AC-027, AC-033, AC-032 (NFR-008 met by AC-to-test coverage) |
| (technical) | NFR-013, NFR-015, NFR-016, NFR-017 | AC-035, AC-036 |

## 8. Ambiguities, missing details and risks

| # | Item | Status |
|---|---|---|
| R-01 | Identity: how "creator" is captured and what "my tickets" means. | RESOLVED v3 (A-02 Approved, D-03): typed name, unverified. |
| R-02 | "Pending" undefined. | RESOLVED: dashboard shows Open and In Progress separately. |
| R-03 | Resolved vs Closed distinction and lifecycle. | Values RESOLVED; transitions OPEN (A-03) |
| R-04 | Priority levels and who changes them. | Levels and engineer change RESOLVED; employee setting at creation OPEN (A-05) |
| R-05 | Fields beyond "details". | Field list RESOLVED; category list RESOLVED v3 (A-18 Approved) |
| R-06 | Assignment to engineer. | RESOLVED: not in scope (no assignee field). |
| R-07 | Comments/history. | RESOLVED by omission: only resolution_note; no history. Confirm. |
| R-08 | Deletion/cancellation/reopening. | Deletion out of scope; reopening depends on A-03. |
| R-09 | Concurrency: last write wins. | OPEN (A-09) |
| R-10 | Data volume/performance. | OPEN (A-10) |
| R-11 | Browser support. | OPEN (A-11) |
| R-12 | "Easy to use" subjective. | OPEN (A-12) |
| R-13 | No backup/retention requirement. | OPEN (A-14) |
| R-14 | Dashboard format. | RESOLVED: counts plus priority and category breakdowns; charts not required, no date filter (A-13). |
| R-15 | Security: no auth; any user can read/modify all data. | ACCEPTED as DEMO limitation; must be disclosed (NFR-009, FR-022, AC-023, AC-031). No security guarantee is made. |
| R-16 | Network access / multi-user. | RESOLVED: local single machine, no deployment (A-15). |
| R-17 | Resolution note visibility to the employee and length. | RESOLVED v3 (A-16 Approved): required for Resolved, visible to creator; length limit per A-06 (still assumption). |
| R-18 | Whether priority/resolution note may be edited on Closed tickets (currently allowed). | OPEN (A-19) |

## 9. Assumptions

| ID | Assumption | Status |
|---|---|---|
| A-01 | Roles are a UI selector with NO login and NO real access control; labeled DEMO and disclosed. | APPROVED (human scope) |
| A-02 | Creator = free-text name (1-100 chars) typed in the sidebar, remembered in session, unverified; anyone can type any name. "My tickets" = case-insensitive, Unicode-aware exact match on that text. | APPROVED / implemented (D-03, human approved architecture) |
| A-03 | Status values Open, In Progress, Resolved, Closed. Transitions: implemented per architecture 7.3 (D-02: lifecycle with Resolved -> In Progress reopen; Closed final). | Values APPROVED; transitions implemented as D-02 (approved with the architecture; analyst note: human to reconfirm if the transition table was not explicitly reviewed) |
| A-04 | Priority values Low, Medium, High, Critical. | APPROVED (human scope) |
| A-05 | Engineer may change priority: APPROVED. Employee chooses priority at creation: OPEN (client said "assign priorities"; approved scope lists only that employees create tickets). Recommended: employee chooses at creation. | Part APPROVED, part OPEN |
| A-06 | Field list is APPROVED (ID, title, description, category, priority, status, creator, created_at, updated_at, resolution_note). Length limits (title 100, description 2000, resolution_note 2000, creator 100) are ASSUMPTIONS. | Fields APPROVED; limits OPEN |
| A-07 | Previously "Pending = Open + In Progress; Resolved = Resolved + Closed". | SUPERSEDED: dashboard shows the four statuses separately (FR-013, FR-014). |
| A-08 | No ticket deletion; no comments/history; only current state plus resolution_note. | RESOLVED by omission from approved scope; human to confirm |
| A-09 | Concurrency: last write wins. | OPEN |
| A-10 | Up to ~1,000 tickets, under 2 seconds. | OPEN |
| A-11 | Current desktop Chrome and Firefox. | OPEN |
| A-12 | "Easy to use" measured by one form with max 5 inputs and plain errors. | OPEN |
| A-13 | Dashboard: numeric counts plus priority and category tables; no date filter. | APPROVED in substance (human scope: counts and breakdowns); chart/no-filter detail is assumption |
| A-14 | Single local SQLite file; no backup/retention; timestamps in UTC. | OPEN |
| A-15 | English-only UI; local single-machine run; no cloud/external APIs. | APPROVED (human scope: no cloud, external APIs, deployment); English-only remains assumption |
| A-16 | Resolution note: a non-blank note is required to move to Resolved; Closed keeps it (a Resolved/Closed ticket always has a note). Engineers may add/edit the note in any status. Visible to the creating employee. | APPROVED / implemented (D-04) |
| A-17 | New tickets start Open; default priority Medium when none is supplied. | ASSUMPTION, needs approval |
| A-18 | Category is a fixed list: Hardware, Software, Network, Access, Other. | APPROVED / implemented (D-01) |
| A-19 | Whether priority and resolution note may be edited on Closed tickets. Currently allowed (Closed blocks only status changes). | OPEN, awaiting human decision |

## 10. Open questions for the human

Resolved by the approved scope:
- Q-01 RESOLVED: DEMO role selector, no real login; disclose in docs (A-01).
- Q-04 PARTLY RESOLVED: priority values and engineer-change approved; employee-sets-at-creation remains (see Q-14).
- Q-05 RESOLVED: dashboard shows Open, In Progress, Resolved, Closed separately (A-07 superseded).
- Q-06 PARTLY RESOLVED: field list approved, assignee excluded; category list remains (Q-04 below, A-18).
- Q-07, Q-08 RESOLVED by omission: no comment/history log, no deletion (human to confirm).
- Q-10 RESOLVED: counts plus priority and category breakdowns.
- Q-11 RESOLVED: no access control exists in the DEMO; the dashboard is only offered on the Manager view, not enforced.
- Q-13 RESOLVED: local only, no cloud or external APIs.

Still open (need human decision):
Resolved v3 (approved with the architecture): Q-02 (A-02, D-03), Q-04 category (A-18, D-01), Q-15 (A-16, D-04). Q-03 transitions: implemented as D-02; reconfirm if not explicitly reviewed.

1. Q-18: May priority and resolution note be edited on Closed tickets (A-19; currently allowed)?
2. Q-14: Does the employee choose priority at creation, and what is the default (A-05, A-17)?
3. Q-09: Confirm volume, performance and browser targets (A-10, A-11).
4. Q-12: Are backups or retention rules needed (A-14)?
5. Q-16: Confirm field length limits (A-06).
6. Q-17: Confirm tickets are never deletable and no comment history is needed (A-08).
7. Q-19: Concurrency last-write-wins (A-09) stays an open assumption; AC-024 stays manual.

## 11. Counts
FR: 22. NFR: 17 (NFR-013..017 added v3). US: 12. AC: 37 (AC-034..037 added v3). Assumptions: 19 (A-19 added v3; A-02, A-16, A-18 closed; A-07 superseded). Open items: A-03 reconfirm, A-05, A-06 limits, A-09, A-10, A-11, A-12, A-14, A-17, A-19.
