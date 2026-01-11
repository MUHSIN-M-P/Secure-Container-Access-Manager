import os 
import sys
import getpass
import subprocess

def _ensure_src_on_path():
    here = os.path.dirname(os.path.abspath(__file__)) #take current path
    src_dir = os.path.join(here, "src") # adds src to that
    if src_dir not in sys.path: # if not found such a path in sys.path 
        sys.path.insert(0, src_dir) #this adding will simplify module import , wihtout worrying about directory, not a really needed function

def verify_linux_password_with_sudo() -> bool:
    """
    Behavior:
    - If running as root: skip (already privileged).
    - If sudo isn't available or user isn't sudoers: fail and tell user what to do.
    """
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("Running as root.")
        return True
    
    pw = getpass.getpass("Linux password (sudo): ")

    try:
        # -S reads password from stdin
        # -v validates cached credentials
        p = subprocess.run(
            ["sudo", "-S", "-v"],
            input=(pw + "\n").encode(),
            stdout=subprocess.PIPE, # Capture output
            stderr=subprocess.PIPE, # Capture errors
            check=False,    # Don't raise exception on error , we will do by code
        )
        # on background it will run "echo "mycorrectpass" | sudo -S -v"
        if p.returncode == 0:
            return True

        err = (p.stderr or b"").decode(errors="ignore").strip()
        print("Password verification failed.")
        if err:
            print("sudo says:", err)
        return False

    except FileNotFoundError:
        print("sudo not found. Install sudo or run this script as root.")
        return False
    
def _run_sudo(cmd, *, input_bytes=None) -> tuple[int, str]:
    """Helper to run a command with sudo and capture output."""
    p = subprocess.run(
        cmd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stderr = (p.stderr or b"").decode(errors="ignore").strip()
    stdout = (p.stdout or b"").decode(errors="ignore").strip()
    return p.returncode, stderr or stdout


def lock_docker_systemwide() -> bool:
    """
    Lock Docker so normal users cannot access /var/run/docker.sock.
    
    How it works (systemd drop-in approach):
    1. Creates /etc/systemd/system/docker.service.d/scam-lock.conf
    2. Adds ExecStartPost hooks to force root-only socket permissions
    3. Reloads systemd and restarts docker
    
    Why this is needed:
    - Prevents users from bypassing the wrapper with direct 'docker exec'
    - Enforces that all container access goes through this gatekeeper
    
    Security note:
    - This does NOT protect against root users
    - Requires removing developers from 'docker' group
    - Requires sudoers policy restricting 'docker' command
    """
    dropin_dir = "/etc/systemd/system/docker.service.d"
    dropin_path = f"{dropin_dir}/scam-lock.conf"
    dropin_content = """[Service]
# Force Docker socket to be root-only (Option 2A: gatekeeper enforcement)
ExecStartPost=/bin/chown root:root /var/run/docker.sock
ExecStartPost=/bin/chmod 0600 /var/run/docker.sock
"""

    print("\n" + "=" * 60)
    print("DOCKER LOCK SETUP")
    print("=" * 60)
    print("Locking /var/run/docker.sock to root-only (0600)...")
    print()

    # Create drop-in directory
    rc, msg = _run_sudo(["sudo", "mkdir", "-p", dropin_dir])
    if rc != 0:
        print(f"Failed to create {dropin_dir}: {msg}")
        return False

    # Write drop-in config
    rc, msg = _run_sudo(["sudo", "tee", dropin_path], input_bytes=dropin_content.encode())
    if rc != 0:
        print(f"Failed to write {dropin_path}: {msg}")
        return False

    print(f"✓ Created {dropin_path}")

    # Reload systemd
    rc, msg = _run_sudo(["sudo", "systemctl", "daemon-reload"])
    if rc != 0:
        print(f"Failed to reload systemd: {msg}")
        return False

    print("✓ Reloaded systemd")

    # Restart docker
    print("Restarting Docker service...")
    rc, msg = _run_sudo(["sudo", "systemctl", "restart", "docker"])
    if rc != 0:
        print(f"Failed to restart docker: {msg}")
        return False

    print("✓ Docker restarted")

    # Verify socket permissions
    rc, output = _run_sudo(["sudo", "ls", "-l", "/var/run/docker.sock"])
    print(f"\nDocker socket permissions:\n{output}")

    print("\n" + "=" * 60)
    print("DOCKER LOCKED SUCCESSFULLY")
    print("=" * 60)
    print("Normal users can no longer run 'docker' commands directly.")
    print("All container access must go through: sudo python setup.py")
    print("=" * 60 + "\n")
    
    return True


def remove_users_from_docker_group() -> bool:
    """
    Automatically remove all non-root users from the docker group.
    This prevents them from bypassing the wrapper.
    """
    print("\n" + "=" * 60)
    print("REMOVING USERS FROM DOCKER GROUP")
    print("=" * 60)
    
    # Get list of users in docker group
    rc, output = _run_sudo(["sudo", "getent", "group", "docker"])
    if rc != 0:
        print("Could not find docker group. Skipping.")
        return True
    
    # Parse: docker:x:999:user1,user2,user3
    parts = output.split(":")
    if len(parts) < 4 or not parts[3].strip():
        print("No users in docker group. Nothing to do.")
        return True
    
    users_in_docker = [u.strip() for u in parts[3].split(",") if u.strip()]
    
    if not users_in_docker:
        print("No users in docker group. Nothing to do.")
        return True
    
    print(f"Found {len(users_in_docker)} user(s) in docker group: {', '.join(users_in_docker)}")
    
    # Remove each user
    failed = []
    for user in users_in_docker:
        print(f"Removing {user} from docker group...")
        rc, msg = _run_sudo(["sudo", "gpasswd", "-d", user, "docker"])
        if rc != 0:
            print(f"  ✗ Failed: {msg}")
            failed.append(user)
        else:
            print(f"  ✓ Removed {user}")
    
    if failed:
        print(f"\n✗ Failed to remove: {', '.join(failed)}")
        return False
    
    print("\n✓ All users removed from docker group")
    print("Note: Users must log out and back in for this to take effect.")
    print("=" * 60 + "\n")
    return True


def setup_developers_group() -> bool:
    """
    Automatically create developers group and add all non-root users to it.
    """
    print("\n" + "=" * 60)
    print("SETTING UP DEVELOPERS GROUP")
    print("=" * 60)
    
    # Check if developers group exists
    rc, _ = _run_sudo(["sudo", "getent", "group", "developers"])
    if rc == 0:
        print("Group 'developers' already exists.")
    else:
        print("Creating 'developers' group...")
        rc, msg = _run_sudo(["sudo", "groupadd", "developers"])
        if rc != 0:
            print(f"✗ Failed to create group: {msg}")
            return False
        print("✓ Created 'developers' group")
    
    # Get all regular users (UID >= 1000, excluding nobody)
    rc, output = _run_sudo(["sudo", "getent", "passwd"])
    if rc != 0:
        print("Failed to get user list")
        return False
    
    regular_users = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 3:
            username = parts[0]
            uid = int(parts[2])
            # Regular users typically have UID >= 1000
            if uid >= 1000 and username != "nobody":
                regular_users.append(username)
    
    if not regular_users:
        print("No regular users found to add to developers group.")
        return True
    
    print(f"\nAdding {len(regular_users)} user(s) to developers group...")
    
    failed = []
    for user in regular_users:
        print(f"Adding {user}...")
        rc, msg = _run_sudo(["sudo", "usermod", "-aG", "developers", user])
        if rc != 0:
            print(f"  ✗ Failed: {msg}")
            failed.append(user)
        else:
            print(f"  ✓ Added {user}")
    
    if failed:
        print(f"\n✗ Failed to add: {', '.join(failed)}")
        return False
    
    print("\n✓ All users added to developers group")
    print("Note: Users must log out and back in for this to take effect.")
    print("=" * 60 + "\n")
    return True


def setup_sudoers_automated() -> bool:
    """
    Automatically create sudoers configuration.
    This writes /etc/sudoers.d/scam with proper permissions and validation.
    """
    # Get absolute path to this script
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    
    sudoers_file = "/etc/sudoers.d/scam"
    sudoers_content = f"""# Secure Container Access Manager - Gatekeeper Policy
# Created automatically by setup.py

# Allow developers to run ONLY the wrapper, not docker directly
# Replace %developers with your actual group name if different
%developers ALL=(root) NOPASSWD: {python_path} {script_path}

# Explicitly deny direct docker access to prevent bypass
%developers ALL=(ALL) !/usr/bin/docker, !/usr/bin/docker-compose
"""

    print("\n" + "=" * 60)
    print("SUDOERS CONFIGURATION (Automated)")
    print("=" * 60)
    print(f"Creating: {sudoers_file}")
    print(f"Script path: {script_path}")
    print(f"Python path: {python_path}")
    print()
    
    # Write sudoers file with strict permissions
    rc, msg = _run_sudo(
        ["sudo", "tee", sudoers_file],
        input_bytes=sudoers_content.encode()
    )
    if rc != 0:
        print(f"Failed to write {sudoers_file}: {msg}")
        return False
    
    # Set proper permissions (0440 is standard for sudoers files)
    rc, msg = _run_sudo(["sudo", "chmod", "0440", sudoers_file])
    if rc != 0:
        print(f"Failed to set permissions on {sudoers_file}: {msg}")
        return False
    
    print(f"✓ Created {sudoers_file}")
    
    # Validate using visudo
    print("Validating sudoers syntax...")
    rc, msg = _run_sudo(["sudo", "visudo", "-c", "-f", sudoers_file])
    if rc != 0:
        print(f"✗ Syntax validation failed: {msg}")
        print("Removing invalid sudoers file...")
        _run_sudo(["sudo", "rm", "-f", sudoers_file])
        return False
    
    print("✓ Sudoers syntax validated")
    
    print("\n" + "=" * 60)
    print("SUDOERS CONFIGURED SUCCESSFULLY")
    print("=" * 60)
    print("Developers in the 'developers' group can now run:")
    print(f"  sudo {python_path} {script_path}")
    print("=" * 60 + "\n")
    
    return True
    
def _print_header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def menu():
    from db import init_db
    import check_docker
    import enter
    import admin as admin_mod
    import user as user_mod
    from accounts import count_users, list_users

    init_db()

    _print_header("Secure Container Access Manager")
    check_docker.check()

    if count_users(role="admin") == 0:
        _print_header("FIRST-TIME SETUP")
        print("No admins found. Running FULLY AUTOMATED initial setup.")
        print("This will configure everything for production security.")
        print()
        
        # Step 1: Lock Docker to enforce gatekeeper
        if not lock_docker_systemwide():
            print("✗ Docker lock failed. Aborting setup.")
            return
        
        # Step 2: Remove users from docker group (prevent bypass)
        if not remove_users_from_docker_group():
            print("✗ Failed to remove users from docker group. Aborting setup.")
            return
        
        # Step 3: Create developers group and add users
        if not setup_developers_group():
            print("✗ Failed to setup developers group. Aborting setup.")
            return
        
        # Step 4: Configure sudoers policy
        if not setup_sudoers_automated():
            print("✗ Sudoers setup failed. Aborting setup.")
            return
        
        # Step 5: Create first admin
        print("\n" + "=" * 60)
        print("FINAL STEP: CREATE FIRST ADMIN")
        print("=" * 60)
        print("All security configurations complete!")
        print("Now create the first admin account.")
        print()
        admin_mod.bootstrap_admin()
        
        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print("✓ Docker locked to root-only")
        print("✓ Users removed from docker group")
        print("✓ Developers group configured")
        print("✓ Sudoers policy active")
        print("✓ First admin created")
        print()
        print("IMPORTANT: All users must log out and back in for changes to take effect.")
        print("=" * 60 + "\n")

    _print_header("MENU")
    print("1) List admins")
    print("2) Add admin")
    print("3) Remove admin")
    print("4) List regular users")
    print("5) Add regular user")
    print("6) Delete regular user")
    print("7) Enter a container (auth + record)")

    choice = input("Select one option: ").strip()

    if choice == "1":
        admins = list_users(role="admin")
        if not admins:
            print("(no admins)")
        else:
            for username, role in admins:
                print(f"- {username} ({role})")
        return

    if choice == "2":
        admin_mod.add_admin()
        return

    if choice == "3":
        admin_mod.remove_admin()
        return

    if choice == "4":
        users = list_users(role="user")
        if not users:
            print("(no regular users)")
        else:
            for username, role in users:
                print(f"- {username} ({role})")
        return

    if choice == "5":
        user_mod.prompt_create()
        return

    if choice == "6":
        admin_mod.delete_regular_user()
        return

    if choice == "7":
        enter.main()
        return

    print("Invalid choice.")
    return


def main():
    _ensure_src_on_path()

    if not verify_linux_password_with_sudo():
        print("Aborting.")
        sys.exit(1)

    menu()


if __name__ == "__main__":
    main()