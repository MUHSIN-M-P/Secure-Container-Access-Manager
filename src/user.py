#!/usr/bin/env python3

import argparse
import getpass

from accounts import create_user, delete_user, list_users, verify_user_password


def prompt_create() -> bool:
    username = input("User username: ").strip()
    pw = getpass.getpass("Password (min 8 chars): ")
    ok, msg = create_user(username, pw, "user")
    print(msg)
    return ok


def prompt_delete() -> bool:
    """Delete own user account after password confirmation."""
    username = input("Username to delete: ").strip()
    pw = getpass.getpass(f"Password for '{username}' (required to confirm): ")
    verified, vmsg = verify_user_password(username, pw)
    if not verified:
        print(vmsg)
        return False
    ok, msg = delete_user(username, role="user")
    print(msg)
    return ok


def _print_users(users: list[tuple[str, str]]):
    if not users:
        print("(none)")
        return
    for username, role in users:
        print(f"- {username} ({role})")


def main():
    parser = argparse.ArgumentParser(description="Manage regular users")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List regular users")
    sub.add_parser("create", help="Create a regular user account")
    sub.add_parser("delete", help="Delete a regular user account (requires password)")

    args = parser.parse_args()

    if args.cmd == "list":
        _print_users(list_users(role="user"))
        return
    if args.cmd == "create":
        prompt_create()
        return
    if args.cmd == "delete":
        prompt_delete()
        return


if __name__ == "__main__":
    main()
