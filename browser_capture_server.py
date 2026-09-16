from __future__ import annotations

import argparse
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from browser_capture import CaptureApplication, DEFAULT_TOKEN_FILE, MAX_CAPTURE_CHARACTERS


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
            status, headers, response = app.handle(
                self.command,
                self.path,
                {key: value for key, value in self.headers.items()},
                body,
            )
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate 0 rendered-DOM capture bridge")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    args = parser.parse_args()
    token = load_or_create_token(args.token_file)
    server = ThreadingHTTPServer(("127.0.0.1", 18431), make_handler(CaptureApplication(token)))
    print("browser capture bridge listening on http://127.0.0.1:18431 (memory-only captures)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
