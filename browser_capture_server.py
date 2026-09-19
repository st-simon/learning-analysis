from __future__ import annotations

import json
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

from browser_capture import (
    CaptureApplication,
    MAX_CAPTURE_CHARACTERS,
)


def load_or_create_token(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "w", encoding="utf-8") as token_file:
            token_file.write(secrets.token_urlsafe(32))
    path.chmod(0o600)
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("capture token is empty")
    return token


def redacted_error_event(
    method: str,
    target: str,
    status: int,
    response: bytes,
    *,
    headers: dict[str, str] | None = None,
    allowed_origin: str | None = None,
) -> dict | None:
    if status < 400:
        return None
    try:
        payload = json.loads(response)
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    if status == 404 and payload.get("status") == "NO_PENDING":
        return None
    path = urlsplit(target).path
    stage = {
        "/pending": "pending",
        "/capture": "capture",
        "/healthz": "health",
    }.get(path, "routing")
    event = {
        "stage": stage,
        "status": "error",
        "request_method": method,
        "http_status": status,
        "error_code": payload.get("error_code", "HTTP_ERROR"),
    }
    if headers is not None and allowed_origin is not None:
        normalized_headers = {key.lower(): value for key, value in headers.items()}
        origin = normalized_headers.get("origin", "")
        if not origin:
            origin_class = "MISSING"
        elif origin == allowed_origin:
            origin_class = "EXACT"
        elif origin == f"{allowed_origin}/":
            origin_class = "EXACT_TRAILING_SLASH"
        elif origin.startswith("chrome-extension://"):
            origin_class = "OTHER_EXTENSION"
        else:
            origin_class = "OTHER"
        event["origin_class"] = origin_class
    return event


def make_handler(app: CaptureApplication):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            self._dispatch(b"")

        def do_OPTIONS(self):
            self._dispatch(b"")

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_CAPTURE_CHARACTERS * 4:
                self.send_error(413)
                return
            self._dispatch(self.rfile.read(length))

        def _dispatch(self, body: bytes):
            request_headers = {key: value for key, value in self.headers.items()}
            status, headers, response = app.handle(
                self.command,
                self.path,
                request_headers,
                body,
            )
            event = redacted_error_event(
                self.command,
                self.path,
                status,
                response,
                headers=request_headers,
                allowed_origin=app.allowed_origin,
            )
            if event is not None:
                print(json.dumps(event, sort_keys=True), file=sys.stderr, flush=True)
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            if response:
                self.wfile.write(response)

        def log_message(self, _format, *_args):
            return

    return Handler
