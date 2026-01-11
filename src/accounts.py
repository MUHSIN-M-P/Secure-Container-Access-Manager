#!/usr/bin/env python3

from __future__ import annotations

import bcrypt

from db import init_db, get_conn


def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt())


def check_password(plain: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed)


def get_user(username: str):
    """Return sqlite Row for user or None."""
    init_db()
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT username, password_hash, role FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    finally:
        conn.close()


def verify_user_password(username: str, plain_password: str) -> tuple[bool, str]:
    """Verify username exists and password matches."""
    username = (username or "").strip()
    if not username:
        return False, "Username can't be empty."

    row = get_user(username)
    if not row:
        return False, f"No such user '{username}'."

    if check_password(plain_password or "", row["password_hash"]):
        return True, "Password verified."
    return False, "Wrong password."


def verify_user_role_password(
    username: str, plain_password: str, required_role: str
) -> tuple[bool, str]:
    """Verify a password and ensure the account has a specific role.

    This is how we enforce admin-only actions at the script level.
    """
    if required_role not in ("admin", "user"):
        return False, "Invalid required_role. Must be 'admin' or 'user'."

    username = (username or "").strip()
    if not username:
        return False, "Username can't be empty."

    row = get_user(username)
    if not row:
        return False, f"No such user '{username}'."

    if row["role"] != required_role:
        return False, f"User '{username}' is not an {required_role}."

    if check_password(plain_password or "", row["password_hash"]):
        return True, "Password verified."
    return False, "Wrong password."


def create_user(username: str, plain_password: str, role: str) -> tuple[bool, str]:
    """Create a user with the given role ('user' or 'admin')."""
    if role not in ("admin", "user"):
        return False, "Invalid role. Must be 'admin' or 'user'."

    username = (username or "").strip()
    if not username:
        return False, "Username can't be empty."

    if len(plain_password or "") < 8:
        return False, "Password needs to be at least 8 characters long."

    init_db()
    conn = get_conn()
    try:
        cur = conn.cursor()
        existing = cur.execute(
            "SELECT username FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing:
            return False, f"User '{username}' already exists."

        hashed = hash_password(plain_password)
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
        conn.commit()
        return True, f"User '{username}' created with role '{role}'."
    finally:
        conn.close()


def delete_user(username: str, *, role: str | None = None) -> tuple[bool, str]:
    """Delete a user.

    If role is provided, deletion is restricted to that role.
    """
    username = (username or "").strip()
    if not username:
        return False, "Username can't be empty."
    if role is not None and role not in ("admin", "user"):
        return False, "Invalid role filter. Must be 'admin', 'user', or omitted."

    init_db()
    conn = get_conn()
    try:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT username, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return False, f"No such user '{username}'."
        if role is not None and row["role"] != role:
            return False, f"User '{username}' is role '{row['role']}', not '{role}'."

        cur.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return True, f"User '{username}' deleted."
    finally:
        conn.close()


def list_users(*, role: str | None = None) -> list[tuple[str, str]]:
    """Return list of (username, role)."""
    if role is not None and role not in ("admin", "user"):
        raise ValueError("role must be 'admin', 'user', or None")

    init_db()
    conn = get_conn()
    try:
        if role is None:
            rows = conn.execute(
                "SELECT username, role FROM users ORDER BY role DESC, username"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT username, role FROM users WHERE role = ? ORDER BY username",
                (role,),
            ).fetchall()
        return [(r["username"], r["role"]) for r in rows]
    finally:
        conn.close()


def count_users(*, role: str | None = None) -> int:
    """Count all users, optionally filtered by role."""
    if role is not None and role not in ("admin", "user"):
        raise ValueError("role must be 'admin', 'user', or None")

    init_db()
    conn = get_conn()
    try:
        if role is None:
            row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE role = ?",
                (role,),
            ).fetchone()
        return int(row["cnt"])
    finally:
        conn.close()
