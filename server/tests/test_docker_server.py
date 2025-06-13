import subprocess
import shutil
import requests
from pathlib import Path

import pytest

from .conftest import find_free_port, wait_for_server_ready


@pytest.mark.integration
@pytest.mark.server
@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker not installed")
def test_docker_container_serves_http():
    """Build Docker image, run container, and verify HTTP endpoint."""
    port = find_free_port()
    repo_root = Path(__file__).resolve().parents[2]
    image_tag = f"mcp-test-image-{port}"

    # Build the Docker image
    subprocess.run([
        "docker",
        "build",
        "-t",
        image_tag,
        str(repo_root),
    ], check=True)

    # Start the container detached mapping the allocated port
    run_cmd = [
        "docker",
        "run",
        "-d",
        "--rm",
        "-p",
        f"{port}:8000",
        image_tag,
    ]
    container_id = subprocess.check_output(run_cmd, text=True).strip()

    try:
        assert wait_for_server_ready(port, timeout=60)
        response = requests.get(f"http://localhost:{port}/", timeout=5)
        assert response.status_code == 200
    finally:
        subprocess.run(["docker", "stop", container_id], check=False)
        subprocess.run(["docker", "rm", "-f", container_id], check=False)
        subprocess.run(["docker", "rmi", "-f", image_tag], check=False)

