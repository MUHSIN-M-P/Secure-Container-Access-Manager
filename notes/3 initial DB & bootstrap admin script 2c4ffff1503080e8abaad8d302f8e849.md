# 3. initial DB & bootstrap admin script

Create `src/db.py` and `src/bootstrap.py`. These two files initialize the SQLite DB and let you create the first admin. 

Run:

```bash
python src/bootstrap.py
```

Follow prompts and create an admin account. Confirm success .

**Why this step**: gives a safe place to store users (SQLite) and ensures the DB schema is correct.

**Edge cases & notes**:

- If you rerun bootstrap after users exist, it will abort (safe).
- If you forget the admin password, you can delete the DB file `~/.secure_container_access.db` and re-bootstrap (this deletes all users and logs) — use carefully.

> Make sure your venv is active (`source .venv/bin/activate`) and you installed `bcrypt` (`pip install bcrypt`) before running the script.
> 

---

db.py

- `DB_PATH`: file path for the database in your home directory.
- `get_conn()`:
    - Creates the directory if it doesn't exist
    - Establishes a database connection with:
        - `timeout=10`: Waits up to 10 seconds if database is locked
        - `check_same_thread=False`: Allows connection sharing across threads
            - multiple connection at a time
        - `row_factory = sqlite3.Row`: Returns rows as dictionary-like objects , so we can access column by name
- `init_db()`: runs SQL to create three tables if they don’t already exist: `users`, `containers`, and `access_logs`.

 `password_hash BLOB NOT NULL,         -- Hashed password (binary)`

BLOB stands for **Binary Large Object**. In databases, it's a data type for storing:

- Raw binary data
- Files (images, PDFs, etc.)
- Serialized objects
- Encrypted/hashed data

---

bootstrap.py
`import getpass          # For secure password input (shows ****, not plain text)`

- `plain.encode()`: Converts string to bytes (bcrypt needs bytes)
- `bcrypt.gensalt()`: Generates a random salt (different salt each time)

```
  conn.commit()  # Save changes
    conn.close()   # Close connection
```

`if __name__ == "__main__":
    bootstrap_admin()`

Only runs when script is executed directly (not imported).

---

# Test Docker SDK connectivity from Python

Create `src/check_docker.py`:

the wrapper will use Docker SDK to ensure the container exists and is running before we attempt to hand over a shell. If the SDK fails but `docker` CLI works, we can rely on the CLI for final `exec` anyway — but SDK checks are nicer.

cli works only if such container exist 

---

**RBAC (Role-Based Access Control)**

RBAC controls **who can do what**.

- **Admin role**: Can enter any container
- **Regular users**: Can only enter containers they own

### **Spawn & Record**

This is the **session recording** system:

**Spawn: Starting a shell inside the container**

The script uses `docker exec -it <container> bash/sh` to spawn a shell.

**Record: Logging all terminal activity**

Two approaches:

1. **`script` command** (preferred if available):
    
    bash
    
    ```
    script -q typescript.log docker exec -it container_name bash
    #script -q <typescript> docker exec -it <container> <shell>
    ```
    
    Records all input/output including terminal control sequences.
    
    - typescript is the name of the file where the script command saves a typescript (a record) of the terminal session.
2. **PTY fallback**: Uses Python's `pty.fork()` to create a pseudo-terminal and capture raw bytes if `script` isn't available.
    - When reading from a terminal, network socket, or file in binary mode, you get raw bytes. Higher-level APIs often decode those bytes into strings (text) or parse them into structured objects. basically byte representation in ascii of command and other things

The recording saves to:

text

```
~/container_sessions/container_user_20241225123045.log
```

With restrictive permissions (`chmod 600`).

---

spawn_and_record(container_name, username):
1. Creates a typescript log file
2. Spawns a shell inside the container via docker exec
3. Records all terminal I/O to the log file
4. Updates DB with session completion time

using `docker exec -it` gives the same experience as direct `docker exec` but wrapping it inside a pty/script lets you capture the entire interactive record (both what you typed and what the container output).
**DB transaction for claiming**: `BEGIN IMMEDIATE` prevents another writer from modifying simultaneously; it’s a lightweight protection for the claim flow. In very high concurrency, consider stronger locks or using Postgres with `SELECT ... FOR UPDATE`.

---

### **SQL Queries Used:**

```sql
# 1. Authenticate user
conn.execute("SELECT username, password_hash, role FROM users WHERE username = ?", (username,))

# 2. Get container owner
conn.execute("SELECT owner_username FROM containers WHERE container_name = ?", (container_name,))

# 3. Claim container (atomic update)
conn.execute("UPDATE containers SET owner_username = ? WHERE container_name = ?", (username, container_name))

# 4. Log session start
conn.execute("INSERT INTO access_logs (username, container_name, typescript_path) VALUES (?, ?, ?)",
             (username, container_name, ts_path))

# 5. Log session end
conn.execute("UPDATE access_logs SET ts_end = CURRENT_TIMESTAMP WHERE id = ?", (log_id,))
```

---

### **Complete Flow:**

User Auth → Check Container Running → Check Ownership → RBAC Check (admin/owner) → Claim if Unclaimed → Spawn Shell + Record → Log Session to DB

---