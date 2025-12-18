# 2. Basic Setup

create a ubuntu container on wsl 2 :
wsl.exe -d ubuntu
cd /mnt/home 

- don’t create in ususal directories of c or m not working

mkdir -p ~/secure-container-access && cd ~/secure-container-access

# create a Python venv and activate it

python3 -m venv .venv
source .venv/bin/activate

# create minimal repo files

git init

1. Install the packages we need:

```bash
pip install --upgrade pip
pip install docker bcrypt

```

1. Create a minimal project layout:

```bash
mkdir -p src tests
cat > src/__main__.py <<'PY'
# placeholder to run as a module
print("Secure Container Access - placeholder")
PY

```

Run to verify:

```bash
python -m src

```

You should see the placeholder message.

---

# Step B — Confirm Docker works from WSL

In WSL run:

```bash
docker version
docker ps

```

If `docker ps` lists running containers (maybe empty), good. If you get permission errors (`Cannot connect to the Docker daemon`), you must ensure Docker Desktop’s WSL integration is enabled and your WSL distro is selected in Docker Desktop settings. Tell me the output or `ok` if both work.

[https://docs.docker.com/desktop/features/wsl/](https://docs.docker.com/desktop/features/wsl/)

---

The error "permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock" indicates that your current user lacks the necessary permissions to interact with the Docker daemon. This is a common issue and can be resolved by adding your user to the docker group.

**Here's how to fix it:**

- Add your user to the `docker` group:

Code

    `sudo usermod -aG docker $USER`

This command adds your current user (`$USER`) to the `docker` group. The `-a` flag appends the user to the group, and `-G` specifies the group. Apply the new group membership.

For the changes to take effect, you need to either log out and log back in, or restart your system