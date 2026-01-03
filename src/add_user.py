#!/usr/bin/env python3

import getpass
from src.db import init_db, get_conn
import bcrypt

def hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt())

def add_user():
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    
    username = input("Username: ").strip()
    if not username:
        print("Oops, username can't be empty!")
        return
    
    # Check if the user already exists
    existing = cur.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        print(f"Sorry, user '{username}' already exists!")
        conn.close()
        return
    
    pw = getpass.getpass("Password (min 8 chars): ")
    if len(pw) < 8:
        print("Password needs to be at least 8 characters long.")
        conn.close()
        return
    
    role = "user"
    
    hashed = hash_password(pw)
    cur.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, hashed, role)
    )
    conn.commit()
    conn.close()
    print(f" User '{username}' created with role '{role}'")

if __name__ == "__main__":
    add_user()
