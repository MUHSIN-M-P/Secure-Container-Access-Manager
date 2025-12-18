# 1. Docker Basics

# Run your first container — “hello-world”

This verifies Docker can pull images and run them:

```powershell
docker run hello-world
```

What it does: Docker pulls the `hello-world` image and runs it; the container prints a short message then exits.

- **Docker Daemon** is the core engine that powers Docker. which manages manages Docker containers, images, networks.
- docker cli send all the commands to daemon and it to it’s part for creating container and fetching image.

---

# Run an interactive Linux shell (practice using containers)

Run an Ubuntu container and get an interactive shell:

```powershell
docker run -it --rm ubuntu:24.04 bash
```

- `it` = interactive terminal
- `-rm` = automatically remove container after exit
- `ubuntu:24.04` = image (use `latest` or specific tag)

**Interactive Terminal (`-it` or `--interactive --tty`)**

- **Interactive shell** (two-way communication)
- **TTY allocation** (terminal emulation)
- **Attached to STDIN** (can receive input)

**Non-Interactive Terminal**

without `-it` or with `-d` (detached):

- **One-way execution**
- **No TTY allocated**
- **STDIN closed** (can't send input after start)

use cases : background services, automation/scripts, CI/CD pipelines

> A **TTY** is a **kernel-level device** that provides text-based communication between processes(os) and users. 
TTY**(TeleTYpewriter)**
> 

---

# Run a background container (detached) and map a port

Run Nginx web server and map container port 80 → host port 8080:

> **NGINX** is a high-performance, open-source **web server**, **reverse proxy**, **load balancer**, and **HTTP cache**.
generally there are 2 types of web servers
1.**Apache (Process-Based/Multi-Threaded) Architecture
2.NGINX (Event-Driven/Asynchronous) Architecture**
> 

```powershell
docker run -d --name mynginx -p 8080:80 nginx:stable
```

- `d` runs detached (background)
- `-name mynginx` gives a name so you can refer easily
- `p 8080:80` maps host port 8080 to container port 80
    - **Container Port** is the **port inside the Docker container** where an application/service is listening for connections.

Open `http://localhost:8080` in your browser — you should see the Nginx welcome page.

To stop and remove it:

```powershell
docker stop mynginx
docker rm mynginx
```

To remove the image if you want to free space:

```powershell
docker rmi nginx:stable
```

---

# Inspect logs & execute commands inside a running container

If container is running:

```powershell
# view logs
docker logs mynginx

# start an interactive shell inside the running container
docker exec -it mynginx /bin/sh   # or /bin/bash if available
```

`docker exec` is the exact command your Secure Container Access Wrapper will wrap. Practice entering and leaving a container using this.

---

# Persist data with volumes

Containers are temporary; use volumes to keep data:

```powershell
# Create a named volume and Run container with volume mounted
docker volume create mydata 
docker run -d --name demo -v mydata:/data nginx
```

Files written to `/data` inside container persist in the Docker volume even after container removal.

You can also mount a host directory (be careful with permissions):

```powershell
docker run -it --rm -v C:\my\host\folder:/mnt/host ubuntu bash
```

```
docker run -d --name demo [IMAGE] [COMMAND]
│        │     │        │
│        │     │        └── Container name ("demo")
│        │     └─────────── Flag: Assign a custom name
│        └───────────────── Flag: Run in detached mode
└────────────────────────── Main command: Run a container
-v mydata:/data
│     │      │
│     │      └── Mount point INSIDE container (/data)
│     └───────── Volume name (mydata)
└─────────────── Volume mount flag
```

---

# Build a simple Docker image from a Dockerfile

Create a directory `myapp` and inside it create a `Dockerfile`:

`Dockerfile`

```docker
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
CMD ["python", "app.py"]
```

Create `app.py`:

```python
print("Hello from inside the image")
```

Build and run:

```powershell
docker build -t myapp:1.0 .
docker run --rm myapp:1.0
```

This shows how you package code into an image.