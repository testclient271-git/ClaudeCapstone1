# IT Support Ticket Management System (local classroom MVP)

Streamlit UI, Python service layer, SQLite (built-in `sqlite3`). Runs locally only; it makes
no network or cloud calls.

## DEMO disclosure (read this first)
The role selector (Employee, Support Engineer, Manager) is a DEMO convenience. It is NOT
authentication and NOT authorization, and it provides no security. Anyone can pick any role
or type any name (the name is not verified), and can view or change any ticket. No
access-control guarantee is made.

This version must not be publicly deployed or used as a secure multi-user application, and
it should not hold confidential data. It is bound to 127.0.0.1 for local classroom use.

Input limits: free-text search is limited to 100 characters; control, zero-width and
bidirectional-override characters are rejected in text inputs; the SQLite file is created
with mode 0600.

## Setup
Requires Python 3.10+.

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Run
Always launch from the repository root. Streamlit reads `.streamlit/config.toml` only from
the current working directory; launched from elsewhere, that hardening is not applied and the
server may listen on all network interfaces with no authentication. The explicit
`--server.address 127.0.0.1` flag keeps it bound to localhost regardless.

    python -m streamlit run app/main.py --server.address 127.0.0.1

The app is served locally (default http://localhost:8501).

## Data location
The SQLite file defaults to `data/tickets.db` under the repository root (created on first
run; `data/` and `*.db` are git-ignored). Override it with the `TICKETS_DB_PATH`
environment variable, for example `TICKETS_DB_PATH=/tmp/demo.db python -m streamlit run app/main.py --server.address 127.0.0.1`.
There are no secrets or credentials anywhere in the project.

## Tests and lint

    python -m pytest -v
    python -m ruff check .

## Layout
- `app/`: Streamlit UI (calls only `ticketing.service`, `ticketing.models`, `ticketing.exceptions`).
- `ticketing/`: service layer (`service.py`), validation, repository (all SQL, parameterized), `db.py`, models.
- `docs/`: requirements, architecture, implementation plan, traceability.
