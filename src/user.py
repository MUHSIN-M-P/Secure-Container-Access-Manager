#!/usr/bin/env python3

import argparse
import getpass

from accounts import create_user, list_users


def prompt_create() -> bool:
    username = input("User username: ").strip()
    pw = getpass.getpass("Password (min 8 chars): ")
    ok, msg = create_user(username, pw, "user")
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
    sub.add_parser("add", help="Add a regular user")

    args = parser.parse_args()

    if args.cmd == "list":
        _print_users(list_users(role="user"))
        return
    if args.cmd == "add":
        prompt_create()
        return


if __name__ == "__main__":
    main()
