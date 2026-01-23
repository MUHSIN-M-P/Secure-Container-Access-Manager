#!/usr/bin/env python3


import os
import sys
import getpass
import sqlite3
import shutil
import pty
import subprocess
from datetime import datetime, timezone
from db import init_db, get_conn
import docker
import bcrypt

# System-wide session recording path
TYPESCRIPT_DIR = "/var/log/secure-container-access/sessions"

# Don't fail on import if directory doesn't exist yet
# It should be created by setup.py
if not os.path.exists(TYPESCRIPT_DIR):
    try:
        os.makedirs(TYPESCRIPT_DIR, mode=0o750, exist_ok=True)
    except PermissionError:
        # Will fail later when trying to record, but allow import
        pass

def check_password(plain, hashed):
    return bcrypt.checkpw(plain.encode(), hashed)

def authenticate():
    username = input("Username: ").strip()
    pw = getpass.getpass("Password: ")
    conn = get_conn()
    row = conn.execute("SELECT username, password_hash, role FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not row:
        print("No such user.")
        return None
    if check_password(pw, row["password_hash"]):
        return {"username": row["username"], "role": row["role"]}
    else:
        print("Wrong password.")
        return None

def check_container_running(container_name):
    client = docker.from_env()
    try:
        cont = client.containers.get(container_name)
    except docker.errors.NotFound:
        return False, "not found"
    except Exception as e:
        return False, f"docker error: {e}"
    # cont.status may be 'created', 'exited', 'running' etc.
    if getattr(cont, "status", None) != "running":
        # sometimes SDK reports stale status; re-inspect:
        try:
            cont.reload()
        except Exception:
            pass
        if getattr(cont, "status", None) != "running":
            return False, f"container not running (status={cont.status})"
    return True, None

def get_container_owner(container_name):
    conn = get_conn()
    row = conn.execute("SELECT owner_username FROM containers WHERE container_name = ?", (container_name,)).fetchone()
    conn.close()
    return row["owner_username"] if row else None

def claim_container_if_unclaimed(container_name, username):
    """
    Try to claim container atomically using a DB transaction.
    Returns True if claimed (or already owned by username), False if owned by someone else.
    """
    conn = get_conn()
    try:
        # acquire write lock to minimize race
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT owner_username FROM containers WHERE container_name = ?", (container_name,)).fetchone()
        if row is None:
            # not present: insert new claimed row
            conn.execute("INSERT INTO containers (container_name, owner_username) VALUES (?, ?)",
                         (container_name, username))
            conn.commit()
            return True, None
        owner = row["owner_username"]
        if owner is None:
            conn.execute("UPDATE containers SET owner_username = ? WHERE container_name = ?", (username, container_name))
            conn.commit()
            return True, None
        if owner == username:
            return True, None
        return False, owner
    except sqlite3.OperationalError as e:
        # lock failure or similar
        conn.rollback()
        return False, f"db error: {e}"
    finally:
        conn.close()

def log_session_start(username, container_name, typescript_path):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO access_logs (username, container_name, typescript_path) VALUES (?, ?, ?)",
              (username, container_name, typescript_path))
    conn.commit()
    lid = c.lastrowid
    conn.close()
    return lid

def log_session_end(log_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE access_logs SET ts_end = CURRENT_TIMESTAMP WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

def _safe_typescript_name(container_name, username):
    """Generate safe typescript filename and ensure directory exists."""
    # Ensure typescript directory exists
    if not os.path.exists(TYPESCRIPT_DIR):
        try:
            os.makedirs(TYPESCRIPT_DIR, mode=0o750, exist_ok=True)
        except PermissionError:
            print(f"Error: Cannot create session recording directory {TYPESCRIPT_DIR}")
            print("Please run 'sudo python3 setup.py' first to initialize the system.")
            raise
    
    safe = "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in f"{container_name}_{username}")
    ts_name = f"{safe}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.log"
    return os.path.join(TYPESCRIPT_DIR, ts_name)

def spawn_and_record(container_name, username):
    """
    Tries to use "script" command if available (nicer with control sequences).
    Otherwise falls back to pty.fork & os-level piping to record raw bytes.
    Returns True on success.
    """
    ts_path = _safe_typescript_name(container_name, username)

    # minimal sanitization for docker exec args:
    if not all(ch.isalnum() or ch in "-_./" for ch in container_name):
        print("Invalid container name characters.")
        return False

    # log DB entry before spawn to get id
    log_id = log_session_start(username, container_name, ts_path)

    shell_candidates = ["/bin/bash", "/bin/sh"]
    # build docker exec arguments; we'll let docker pick a shell (try bash then sh)
    # Determine if `script` is available
    script_bin = shutil.which("script")

    try:
        print("Starting session. Typescript:", ts_path)
        print("Type 'exit' or Ctrl-D to finish the session.")

        if script_bin:
            # Use script to record: script -q <ts_path> -c "docker exec -it <container> <shell>"
            # For portability pass an explicit shell; we try bash first then sh.
            for sh in shell_candidates:
                cmd = ["script", "-q", ts_path, "-c", f"docker exec -it {container_name} {sh}"]
                # run as subprocess so we can continue afterwards
                rc = subprocess.call(cmd)
                if rc == 0:
                    break
                # non-zero return likely means shell not found inside container; try next shell
            else:
                print("Failed to start shell inside container (tried bash/sh).")
                return False
        else:
            # fallback: pty.spawn approach using fork
            master_fd, slave_fd = pty.openpty()
            pid = os.fork()
            if pid == 0:
                # child -> become the docker exec process attached to pty slave
                os.setsid()
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                if slave_fd > 2:
                    os.close(slave_fd)
                # try each shell candidate; if bash not present docker will return non-zero and exit
                for sh in shell_candidates:
                    os.execvp("docker", ["docker", "exec", "-it", container_name, sh])
                # if exec returns, exit child
                os._exit(127)
            else:
                # parent: read from master_fd and write both to stdout and logfile
                with open(ts_path, "wb") as f:
                    try:
                        while True:
                            try:
                                data = os.read(master_fd, 4096)
                            except OSError:
                                break
                            if not data:
                                break
                            # write to terminal
                            os.write(sys.stdout.fileno(), data)
                            # write to file
                            f.write(data)
                            f.flush()
                    finally:
                        # ensure child cleaned up
                        try:
                            os.waitpid(pid, 0)
                        except ChildProcessError:
                            pass

        # set restrictive perms on log
        try:
            os.chmod(ts_path, 0o600)
        except Exception:
            pass

        print("Session finished. Typescript saved to:", ts_path)
        return True
    except KeyboardInterrupt:
        print("\nSession interrupted.")
        return False
    except Exception as e:
        print("Error during session:", e)
        return False
    finally:
        # ensure we always write session end timestamp
        try:
            log_session_end(log_id)
        except Exception:
            pass

def main():
    init_db()
    user = authenticate()
    if not user:
        return
    # Check if container name provided as argument
    if len(sys.argv) > 1:
        container = sys.argv[1].strip()
    else:
        container = input("Container to enter: ").strip()
    ok, err = check_container_running(container)
    if not ok:
        print("Cannot enter:", err)
        return

    owner = get_container_owner(container)
    if owner is None:
        print("Container is unclaimed.")
        want = input("Claim container and become owner? (y/N): ").strip().lower()
        if want == 'y':
            claimed, info = claim_container_if_unclaimed(container, user["username"])
            if not claimed:
                print("Could not claim container. Owner:", info)
                return
            else:
                print("Claim successful. You are now owner of", container)
        else:
            print("Not claiming. Aborting.")
            return

    owner = get_container_owner(container)  # refresh
    if user["role"] == "admin" or user["username"] == owner:
        success = spawn_and_record(container, user["username"])
        if success:
            print("Goodbye.")
        else:
            print("Session failed or interrupted.")
    else:
        print(f"Access denied. Owner: {owner}. Your role: {user['role']}")

if __name__ == "__main__":
    main()
