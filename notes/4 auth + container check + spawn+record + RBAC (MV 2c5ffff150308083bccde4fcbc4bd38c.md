# 4. auth + container check + spawn+record + RBAC (MVP)

Create `src/enter.py` — this implements: prompt username/password, verify from DB, check container exists and running via Docker SDK, then print a message (we will not exec yet). This lets us test auth and container checks safely.

**Why this step**: isolates authentication and container checks before we attempt to deal with pseudo-ttys and recording — smaller steps reduce confusion.

- Checks container exists and is running (via Docker SDK).
- If unclaimed, lets the authenticated user claim it (with DB-level transaction to reduce race).
- Launches an interactive `docker exec -it <container> <shell>` session **from Python** while recording everything to a timestamped logfile in `~/container_sessions`.
- Writes an `access_logs` DB entry with start and end timestamps and the path to the typescript.
- `authenticate()` — asks username/password and verifies them using bcrypt against your SQLite DB.
- `check_container_running()` — uses Docker SDK to confirm the container is present and running.
- `claim_container_if_unclaimed()` — attempts to claim a previously-unassigned container using a database transaction (`BEGIN IMMEDIATE`) to reduce race conditions.
- `spawn_and_record()` — records the entire interactive session:
    - prefers `script` if available (nicer recording),
    - otherwise falls back to using a pseudo-terminal (`pty`) and forking to run `docker exec`.
    - logs are stored under `~/container_sessions` with restrictive permissions.
- Every session has an `access_logs` row created at start and updated with `ts_end` at completion (even if interrupted).