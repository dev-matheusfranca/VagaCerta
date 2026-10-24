import socket
import threading
import time

import pytest
import uvicorn


@pytest.fixture(scope="module")
def serve():
    """Sobe apps ASGI num uvicorn em segundo plano, cada um numa porta livre, e devolve a URL."""
    servers = []

    def start(app) -> str:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="warning"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        while not server.started:
            time.sleep(0.05)
        servers.append((server, thread))
        return f"http://127.0.0.1:{port}"

    yield start
    for server, thread in servers:
        server.should_exit = True
        thread.join()
