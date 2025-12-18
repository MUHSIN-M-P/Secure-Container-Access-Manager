import getpass
from db import init_db, get_conn
import bcrypt

def hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt())

def bootstrap_admin():
    init_db()
    conn = get_conn()
    cur = conn.cursor()         # pointer to db
    cur.execute("SELECT COUNT(*) as cnt FROM users")
    if cur.fetchone()["cnt"] > 0:   #prevents multiple admins
        print("Users already exist. Aborting bootstrap.")
        return

    username = input("Admin username: ").strip()
    if not username:
        print("Invalid username")
        return
    pw = getpass.getpass("Admin password (min 8 chars): ")
    if len(pw) < 8:
        print("Password too short")
        return
    hashed = hash_password(pw)
    cur.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
        (username, hashed)
    )
    conn.commit()
    conn.close()
    print("Admin created:", username)

if __name__ == "__main__":
    bootstrap_admin()
