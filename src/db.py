import sqlite3
import os

# All users must share the same auth database
DB_PATH = "/var/lib/secure-container-access/db.sqlite"

def get_conn():
    # Directory should already exist from setup.py
    # But try to create it anyway for compatibility
    try:
        os.makedirs(os.path.dirname(DB_PATH), mode=0o755, exist_ok=True)
    except PermissionError:
        print(f"Error: Cannot access {os.path.dirname(DB_PATH)}")
        print("Please run 'sudo python3 setup.py' first to initialize the system.")
        raise
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    except PermissionError:
        print(f"Error: Cannot access database at {DB_PATH}")
        print("Please run 'sudo python3 setup.py' first to initialize the system.")
        raise
    
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY,
      username TEXT UNIQUE NOT NULL,
      password_hash BLOB NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('admin','user')),	--role constrain admin/user only possilbe 
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS containers (
      id INTEGER PRIMARY KEY,
      container_name TEXT UNIQUE NOT NULL,
      owner_username TEXT,
      FOREIGN KEY(owner_username) REFERENCES users(username)
    );
    CREATE TABLE IF NOT EXISTS access_logs (
      id INTEGER PRIMARY KEY,
      username TEXT NOT NULL,
      container_name TEXT NOT NULL,
      ts_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,	-- start time
      ts_end TIMESTAMP,					-- end time
      typescript_path TEXT NOT NULL			-- Path to session recording/script
    );
    """)
    conn.commit()
    conn.close()
