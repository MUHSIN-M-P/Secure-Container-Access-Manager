# 5. implement (MVP-safe)

## **Step 1: Remove Users from Docker Group**

First, check which users are currently in the `docker` group:

```bash
# List current docker group members
getent group docker

# Remove each user from docker group (replace <user> with actual username)
sudo gpasswd -d <username> docker
```

## **Step 2: Create Dedicated Service Account**

Create a new system user specifically for Docker operations:

bash

```bash
# Create the service account
sudo useradd -r -s /bin/false -m -d /home/dockeruser dockeruser

# Add to docker group (this user will have Docker access)
sudo usermod -aG docker dockeruser

# Verify
id dockeruser
```

## **Step 3: Configure Sudoers**

Edit sudoers file securely:

bash

```bash
sudo visudo
```

Add this line at the end of the file:

text

```bash
%scam-users ALL=(dockeruser) NOPASSWD: /usr/bin/docker exec *
```

If the `scam-users` group doesn't exist, create it first:

bash

```bash
# Create the group
sudo groupadd scam-users

# Add users to this group
sudo usermod -aG scam-users alice
sudo usermod -aG scam-users bob

# Verify
getent group scam-users
```

## **Step 4: Test the Setup**

1. **Test as regular user:**

bash

```bash
# Try direct docker command (should fail)
docker ps

```

```bash
~/project$ docker ps
permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock: Get "http://%2Fvar%2Frun%2Fdocker.sock/v1.51/containers/json": dial unix /var/run/docker.sock: connect: permission denied
```

---

```bash
~/project/src ./enter.py enter mynginx
/usr/bin/env: ‘python3\r’: No such file or directory
/usr/bin/env: use -[v]S to pass options in shebang lines
```

```bash
sed -i 's/\r$//' [enter.py](http://enter.py/) # Convert CRLF → LF
```