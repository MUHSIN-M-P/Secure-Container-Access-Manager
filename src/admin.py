#!/usr/bin/env python3

import argparse
import getpass

from accounts import (
        count_users,
        create_user,
        delete_user,
        list_users,
        verify_user_password,
    verify_user_role_password,
)


def _count_admins() -> int:
    return count_users(role="admin")


def _print_admins():
    admins = list_users(role="admin")
    if not admins:
        print("(no admins)")
        return
    for username, role in admins:
        print(f"- {username} ({role})")


def bootstrap_admin() -> bool:
    """Create the first admin if no admins exist.

    Why this changed from the old version:
    - Previously it blocked if *any* user existed.
    - Now it blocks only if an admin already exists, which lets you re-run setup
      later to add more admins.
    """
    if _count_admins() > 0:
        print("Admin already exists. Bootstrap not needed.")
        return False

    username = input("Admin username: ").strip()
    if not username:
        print("Invalid username")
        return False

    pw = getpass.getpass("Admin password (min 8 chars): ")
    ok, msg = create_user(username, pw, "admin")
    print(msg)
    return ok


def add_admin() -> bool:
    username = input("Admin username: ").strip()
    if not username:
        print("Invalid username")
        return False
    pw = getpass.getpass("Admin password (min 8 chars): ")
    ok, msg = create_user(username, pw, "admin")
    print(msg)
    return ok


def remove_admin() -> bool:
    """Delete an admin account.

    Safety rule:
    - Prevent deleting the last remaining admin.
    """
    admins = list_users(role="admin")
    if not admins:
        print("No admins exist.")
        return False

    if len(admins) == 1:
        print("Refusing to delete the last admin.")
        return False

    username = input("Admin username to delete: ").strip()

    # Require the admin's own password to delete that admin.
    pw = getpass.getpass(f"Password for '{username}' (required to delete): ")
    verified, vmsg = verify_user_password(username, pw)
    if not verified:
        print(vmsg)
        return False

    ok, msg = delete_user(username, role="admin")
    if ok:
        # Re-check after delete; still keep the last-admin protection as a guard.
        if _count_admins() == 0:
            print("Refusing to leave system without admins; rolling back isn't supported.")
            print("Please recreate an admin immediately.")
    print(msg)
    return ok


def delete_regular_user() -> bool:
    """Delete a regular user (role='user').

    Requirement:
    - Any admin can delete any regular user *without the user's password*.
    - But we still authenticate the caller as an admin first.
    """
    admin_username = input("Admin username (for authorization): ").strip()
    admin_pw = getpass.getpass(f"Password for '{admin_username}': ")
    verified, vmsg = verify_user_role_password(admin_username, admin_pw, "admin")
    if not verified:
        print(vmsg)
        return False

    username = input("Regular username to delete: ").strip()
    ok, msg = delete_user(username, role="user")
    print(msg)
    return ok


def main():
    parser = argparse.ArgumentParser(description="Bootstrap and manage admin users")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("bootstrap", help="Create first admin if none exist")
    sub.add_parser("list", help="List admins")
    sub.add_parser("add", help="Add an admin")
    sub.add_parser("remove", help="Remove an admin")
    sub.add_parser("delete-user", help="Delete a regular user (admin-only)")

    args = parser.parse_args()

    if args.cmd == "bootstrap":
        bootstrap_admin()
        return
    if args.cmd == "list":
        _print_admins()
        return
    if args.cmd == "add":
        add_admin()
        return
    if args.cmd == "remove":
        remove_admin()
        return
    if args.cmd == "delete-user":
        delete_regular_user()
        return


if __name__ == "__main__":
    main()
