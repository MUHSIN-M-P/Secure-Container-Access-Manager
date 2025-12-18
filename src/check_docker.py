import docker

def check():
    try:
        client = docker.from_env()
        info = client.ping()  # raises if not reachable
        print("Docker API reachable (ping ok).")
    except Exception as e:
        print("Docker API error:", e)

if __name__ == "__main__":
    check()
