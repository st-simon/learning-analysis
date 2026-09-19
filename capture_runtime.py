from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

from browser_capture import (
    CaptureApplication,
    CaptureCoordinator,
    CaptureError,
    DEFAULT_EXTENSION_ID,
)
from browser_capture_server import make_handler


class CaptureRuntime:
    """Owns the in-memory coordinator and its extension-only loopback adapter."""

    def __init__(
        self,
        *,
        token: str,
        extension_id: str = DEFAULT_EXTENSION_ID,
        host: str = "127.0.0.1",
        port: int = 18431,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("capture runtime must bind to loopback")
        if port < 0 or port > 65535:
            raise ValueError("invalid capture runtime port")
        self._host = host
        self._port = port
        self._coordinator = CaptureCoordinator()
        self._application = CaptureApplication(
            token=token,
            extension_id=extension_id,
            coordinator=self._coordinator,
        )
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        with self._lock:
            if self._server is None:
                raise CaptureError("CAPTURE_BRIDGE_UNAVAILABLE")
            host, port = self._server.server_address[:2]
            return f"http://{host}:{port}"

    def start(self) -> None:
        with self._lock:
            if self._server is not None:
                return
            server = ThreadingHTTPServer(
                (self._host, self._port),
                make_handler(self._application),
            )
            thread = threading.Thread(
                target=server.serve_forever,
                name="learning-analysis-capture",
                daemon=True,
            )
            self._server = server
            self._thread = thread
            thread.start()

    def stop(self) -> None:
        with self._lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None
        self._coordinator.cancel_all()
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None:
            thread.join(2)

    def health(self) -> dict:
        with self._lock:
            ready = bool(
                self._server is not None
                and self._thread is not None
                and self._thread.is_alive()
            )
        return {
            "status": "ok" if ready else "stopped",
            "ready": ready,
        }

    def request_capture(
        self,
        source_url: str,
        *,
        request_id: str,
        timeout: float,
    ) -> dict:
        with self._lock:
            ready = bool(
                self._server is not None
                and self._thread is not None
                and self._thread.is_alive()
            )
            if not ready:
                raise CaptureError("CAPTURE_BRIDGE_UNAVAILABLE")
            self._coordinator.begin(source_url, request_id)
        return self._coordinator.wait(request_id, timeout)

    def __enter__(self) -> CaptureRuntime:
        self.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()
