# Project Instructions

## Project Purpose
Enterprise-grade Python application built with an AI engineering team: Streamlit UI, Python service layer, SQLite persistence (built-in `sqlite3`). The concrete application scope will be supplied by the human client as requirements. Project documentation lives in `docs/`.

## Lead Orchestrator Responsibilities
The main Claude Code session is the Lead Orchestrator. It:
- Receives client requirements and coordinates the workflow: requirements -> architecture -> implementation -> QA -> security review -> sign-off.
- Delegates all meaningful work to the subagents below and passes each one the context it needs (it only sees its prompt).
- Reviews subagent output, resolves conflicts, and tracks open questions, defects and status.
- Presents decisions and checkpoints to the human and waits for approval.
- Does NOT impersonate a subagent role: it does not write requirements, designs, application code, tests or security reviews itself.

## Available Subagents (`.claude/agents/`)
| Agent | Responsibility |
|---|---|
| `requirements-analyst` | Analyze requirements; find ambiguities/assumptions; write user stories, functional requirements, acceptance criteria. No code. |
| `solution-architect` | Architecture, modules, data model, SQLite schema, layer interfaces, implementation plan. No code. |
| `backend-developer` | Python business logic, validation, SQLite persistence via `sqlite3`; owns backend/db files. |
| `frontend-developer` | Streamlit UI: forms, tables, filters, dashboards; uses service interfaces only; owns UI files. |
| `qa-engineer` | pytest tests, acceptance/edge-case verification, defect reports with evidence. Does not change production code. |
| `security-reviewer` | Validation, SQL injection, secrets, permissions, workflow review; severity-rated findings; no fixes without retest. |

## Mandatory Delegation Rules
- Requirements analysis -> `requirements-analyst`; design/schema/interfaces -> `solution-architect`; backend code -> `backend-developer`; UI code -> `frontend-developer`; tests -> `qa-engineer`; security review -> `security-reviewer`.
- The orchestrator must not write application code, tests or role-specific documents directly.
- Defects go back to the owning developer agent for fixing, then to `qa-engineer` (and `security-reviewer` where relevant) for retest.
- Independent tasks may be delegated in parallel; dependent tasks run in sequence.

## Planning Before Coding
- No implementation begins until requirements are documented (`docs/requirements.md`) and the architecture and implementation plan (`docs/architecture.md`, `docs/implementation-plan.md`) exist and the human has approved them.
- Developer agents implement against the approved interface contracts; contract changes require re-approval.

## Agent File Ownership
- `docs/requirements.md`, `docs/traceability.md` (structure): requirements-analyst
- `docs/architecture.md`, `docs/implementation-plan.md`: solution-architect
- Backend service/repository/model/database files: backend-developer
- Streamlit UI files: frontend-developer
- `tests/`, pytest config, QA reports: qa-engineer (also updates the test column of the traceability matrix)
- `docs/security-review.md`: security-reviewer
- `CLAUDE.md`, `.claude/`: orchestrator/human only
- No agent edits files it does not own; cross-ownership change requests go through the orchestrator.

## Testing and Quality Requirements
- Every acceptance criterion has at least one pytest test; edge cases and validation failures are covered.
- All SQL is parameterized; the UI contains no SQL; no secrets in code or repo.
- Tests must run and pass (with real output as evidence) before any work is declared done.
- Code uses type hints and docstrings; failures are reported honestly, never hidden by weakening tests.
- Security review is completed and High/Critical findings are fixed and retested before sign-off.

## Human Approval Checkpoints
The orchestrator must stop and get explicit human approval at:
1. Resolution of requirements open questions/assumptions and approval of requirements.
2. Approval of architecture, schema and implementation plan.
3. Installing new dependencies.
4. Completion of implementation, before final QA/security sign-off.
5. Final acceptance of the delivered work.

## Requirement Traceability
- Every requirement has a stable ID (US-###, FR-###, NFR-###) and acceptance criteria.
- `docs/traceability.md` maps requirement -> design element -> code module -> test(s) -> status.
- Code docstrings and test names/markers reference requirement IDs. Any requirement without a test, or code without a requirement, is flagged.

## Deployment
- No cloud deployment, cloud resource creation, or external publishing without explicit human approval. Development and testing are local only.
