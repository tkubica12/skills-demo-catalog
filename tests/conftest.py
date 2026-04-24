from __future__ import annotations

import importlib.util
import os
import socket
import threading
import time
import urllib.request
from pathlib import Path

import pytest


def _load_mock_server_module():
    module_path = Path(__file__).with_name("mock_api_server.py")
    spec = importlib.util.spec_from_file_location("task_api_mock_server", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _select_port() -> int:
    for port in (18080, 0):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return int(sock.getsockname()[1])
        except OSError:
            continue
    raise RuntimeError("Unable to allocate a port for the mock server.")


@pytest.fixture(scope="session", autouse=True)
def mock_server():
    original_base_url = os.environ.get("TASK_API_URL")
    original_token = os.environ.get("TASK_API_TOKEN")

    if original_base_url:
        yield original_base_url
        return

    mock_module = _load_mock_server_module()
    port = _select_port()
    server = mock_module.create_server(port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    os.environ["TASK_API_URL"] = base_url
    os.environ.pop("TASK_API_TOKEN", None)

    try:
        for _ in range(20):
            try:
                with urllib.request.urlopen(f"{base_url}/health", timeout=1):
                    break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("Mock server did not become ready in time.")

        yield base_url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

        if original_base_url is None:
            os.environ.pop("TASK_API_URL", None)
        else:
            os.environ["TASK_API_URL"] = original_base_url

        if original_token is None:
            os.environ.pop("TASK_API_TOKEN", None)
        else:
            os.environ["TASK_API_TOKEN"] = original_token
