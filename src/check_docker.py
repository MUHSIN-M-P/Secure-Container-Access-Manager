import docker
import sys

def check():
    """Check if Docker is available and running."""
    try:
        client = docker.from_env()
        info = client.ping()  # raises if not reachable
        print("✓ Docker API reachable (ping ok).")
        return True
    except docker.errors.DockerException as e:
        print("✗ Docker API error:", e)
        print("\nMake sure Docker is installed and running:")
        print("  sudo systemctl start docker")
        print("  sudo systemctl enable docker")
        return False
    except Exception as e:
        print("✗ Unexpected error:", e)
        return False

if __name__ == "__main__":
    if not check():
        sys.exit(1)
