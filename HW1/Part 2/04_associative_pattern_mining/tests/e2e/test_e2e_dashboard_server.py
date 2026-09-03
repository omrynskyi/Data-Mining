"""
tests/e2e/test_e2e_dashboard_server.py
Tier 4 Real-World Workload & Acceptance Tests: Dashboard Subprocess Startup, Port Binding & Health (Scenario S3).
Spawns `python app.py` as an independent OS subprocess, polls `GET /health` for HTTP 200 OK,
verifies root UI rendering, and ensures graceful server termination.
"""

import os
import sys
import time
import socket
import subprocess
import urllib.request
import urllib.error
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def get_free_port():
    """Find a random available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestE2EDashboardServerLifecycle:
    """Tier 4: Scenario S3 - Subprocess Server Startup & Health Probe."""

    def test_dashboard_subprocess_startup_and_health(self):
        """Spawns `python app.py`, polls /health for 200 OK within 10s, and shuts down cleanly."""
        if not os.path.exists(os.path.join(PROJECT_ROOT, "app.py")):
            pytest.skip("app.py server entrypoint not yet created")

        port = get_free_port()
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["HOST"] = "127.0.0.1"

        cmd = [sys.executable, os.path.join(PROJECT_ROOT, "app.py")]
        proc = subprocess.Popen(cmd, env=env, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        health_url = f"http://127.0.0.1:{port}/health"
        root_url = f"http://127.0.0.1:{port}/"

        healthy = False
        start_time = time.time()
        
        try:
            # Poll /health with 10-second timeout
            while time.time() - start_time < 10.0:
                if proc.poll() is not None:
                    # Process died unexpectedly
                    stdout, stderr = proc.communicate()
                    pytest.fail(f"app.py exited prematurely with code {proc.returncode}:\nSTDOUT:\n{stdout.decode()}\nSTDERR:\n{stderr.decode()}")
                
                try:
                    with urllib.request.urlopen(health_url, timeout=1.0) as response:
                        if response.status == 200:
                            healthy = True
                            break
                except (urllib.error.URLError, ConnectionRefusedError, socket.timeout):
                    time.sleep(0.3)

            assert healthy, f"Dashboard failed to respond with 200 OK on {health_url} within 10 seconds"

            # Check root UI page
            with urllib.request.urlopen(root_url, timeout=2.0) as root_resp:
                assert root_resp.status == 200

        finally:
            # Terminate subprocess gracefully
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
