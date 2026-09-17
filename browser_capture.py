from __future__ import annotations

import threading
import hmac
import json
import os
import re
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx


MAX_CAPTURE_CHARACTERS = 4_000_000
DEFAULT_CAPTURE_ENDPOINT = "http://127.0.0.1:18431/capture"
DEFAULT_TOKEN_FILE = Path(__file__).resolve().parent / "runtime" / "browser-capture.token"
DEFAULT_EXTENSION_ID = "bpannmkojgebmphkkngpnhkfcgfpnbhn"
MAX_CAPTURE_WAIT_SECONDS = 30.0
EXTENSION_ID_PATTERN = re.compile(r"[a-p]{32}")


class CaptureError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _validate_source_url(value: object) -> str:
    if not isinstance(value, str) or len(value) > 8192:
        raise CaptureError("INVALID_SOURCE_URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "mp.weixin.qq.com"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not parsed.path.startswith("/s/")
    ):
        raise CaptureError("INVALID_SOURCE_URL")
    return value


def normalize_capture(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise CaptureError("INVALID_CAPTURE")
    source_url = _validate_source_url(payload.get("source_url"))
    title = payload.get("title")
    markdown = payload.get("markdown")
    if payload.get("source_channel") != "rendered_dom":
        raise CaptureError("INVALID_SOURCE_CHANNEL")
    if not isinstance(title, str) or not title.strip():
        raise CaptureError("EMPTY_TITLE")
    if not isinstance(markdown, str) or not markdown.strip():
        raise CaptureError("EMPTY_ARTICLE")
    if len(markdown) > MAX_CAPTURE_CHARACTERS:
        raise CaptureError("CAPTURE_TOO_LARGE")
    return {
        "status": "ok",
        "source_channel": "rendered_dom",
        "source_url": source_url,
        "title": title.strip(),
        "markdown": markdown,
        "characters": len(markdown),
        "network_used": False,
        "persistent_write": False,
        "warnings": [],
        "limitations": "Rendered DOM only; hidden, unloaded, canvas, or image-only text may be omitted.",
    }


class CaptureStore:
    """Process-memory capture store; intentionally has no persistence adapter."""

    def __init__(self) -> None:
        self._captures: dict[str, dict] = {}
        self._lock = threading.Lock()

    def put(self, capture: dict) -> None:
        with self._lock:
            self._captures[capture["source_url"]] = deepcopy(capture)

    def get(self, source_url: str) -> dict:
        _validate_source_url(source_url)
        with self._lock:
            capture = self._captures.get(source_url)
            if capture is None:
                raise CaptureError("CAPTURE_NOT_FOUND")
            return deepcopy(capture)


@dataclass
class _PendingCapture:
    source_url: str
    capture: dict | None = None
    cancelled: bool = False


class CaptureCoordinator:
    """Coordinates one pending, memory-only browser capture per source URL."""

    def __init__(self) -> None:
        self._pending: dict[str, _PendingCapture] = {}
        self._request_by_url: dict[str, str] = {}
        self._condition = threading.Condition()

    def begin(self, source_url: str, request_id: str) -> None:
        source_url = _validate_source_url(source_url)
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            raise CaptureError("INVALID_REQUEST_ID")
        with self._condition:
            if request_id in self._pending or source_url in self._request_by_url:
                raise CaptureError("CAPTURE_BUSY")
            self._pending[request_id] = _PendingCapture(source_url=source_url)
            self._request_by_url[source_url] = request_id

    def accept(self, capture: dict) -> str:
        source_url = capture["source_url"]
        with self._condition:
            request_id = self._request_by_url.get(source_url)
            if request_id is None:
                raise CaptureError("CAPTURE_NOT_FOUND")
            pending = self._pending[request_id]
            if pending.cancelled or pending.capture is not None:
                raise CaptureError("CAPTURE_NOT_FOUND")
            pending.capture = deepcopy(capture)
            self._condition.notify_all()
            return request_id

    def wait(self, request_id: str, timeout: float) -> dict:
        if timeout < 0 or timeout > MAX_CAPTURE_WAIT_SECONDS:
            raise CaptureError("INVALID_WAIT_SECONDS")
        deadline = time.monotonic() + timeout
        with self._condition:
            pending = self._pending.get(request_id)
            if pending is None:
                raise CaptureError("CAPTURE_NOT_FOUND")
            while pending.capture is None and not pending.cancelled:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._remove(request_id, pending.source_url)
                    raise CaptureError("CAPTURE_TIMEOUT")
                self._condition.wait(remaining)
            self._remove(request_id, pending.source_url)
            if pending.cancelled:
                raise CaptureError("CAPTURE_CANCELLED")
            return deepcopy(pending.capture)

    def cancel(self, request_id: str) -> None:
        with self._condition:
            pending = self._pending.get(request_id)
            if pending is None:
                raise CaptureError("CAPTURE_NOT_FOUND")
            pending.cancelled = True
            self._condition.notify_all()

    def _remove(self, request_id: str, source_url: str) -> None:
        self._pending.pop(request_id, None)
        if self._request_by_url.get(source_url) == request_id:
            self._request_by_url.pop(source_url, None)


class CaptureApplication:
    """Pure request handler shared by the loopback HTTP adapter and unit tests."""

    def __init__(
        self,
        token: str,
        extension_id: str,
        coordinator: CaptureCoordinator | None = None,
    ) -> None:
        if not token:
            raise ValueError("token is required")
        if not EXTENSION_ID_PATTERN.fullmatch(extension_id):
            raise ValueError("valid extension_id is required")
        self._token = token
        self._allowed_origin = f"chrome-extension://{extension_id}"
        self._coordinator = coordinator or CaptureCoordinator()

    def _authorized(self, headers: dict[str, str]) -> bool:
        return hmac.compare_digest(
            headers.get("authorization", ""), f"Bearer {self._token}"
        )

    @staticmethod
    def _json(status: int, payload: dict) -> tuple[int, dict[str, str], bytes]:
        body = json.dumps(payload, ensure_ascii=False).encode()
        return status, {"Content-Type": "application/json", "Cache-Control": "no-store"}, body

    def handle(self, method: str, target: str, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], bytes]:
        headers = {key.lower(): value for key, value in headers.items()}
        parsed = urlsplit(target)
        origin = headers.get("origin", "")
        try:
            if method == "OPTIONS" and parsed.path == "/capture":
                if origin != self._allowed_origin:
                    raise CaptureError("FORBIDDEN_ORIGIN")
                return 204, {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "POST",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type",
                    "Cache-Control": "no-store",
                }, b""
            if method == "GET" and parsed.path == "/healthz":
                return self._json(200, {"status": "ok", "persistent_write": False})
            if method == "POST" and parsed.path == "/capture":
                if origin != self._allowed_origin:
                    raise CaptureError("FORBIDDEN_ORIGIN")
                if not self._authorized(headers):
                    return self._json(401, {"status": "error", "error_code": "UNAUTHORIZED"})
                if len(body) > MAX_CAPTURE_CHARACTERS * 4:
                    raise CaptureError("CAPTURE_TOO_LARGE")
                capture = normalize_capture(json.loads(body))
                request_id = self._coordinator.accept(capture)
                status, response_headers, response_body = self._json(202, {
                    "status": "accepted",
                    "request_id": request_id,
                    "characters": capture["characters"],
                    "persistent_write": False,
                })
                response_headers["Access-Control-Allow-Origin"] = origin
                return status, response_headers, response_body
            if method == "GET" and parsed.path == "/capture":
                if not self._authorized(headers):
                    return self._json(401, {"status": "error", "error_code": "UNAUTHORIZED"})
                values = parse_qs(parsed.query, strict_parsing=True)
                source_url = values.get("url", [None])[0]
                request_id = values.get("request_id", [None])[0]
                try:
                    wait_seconds = float(values.get("wait_seconds", ["0"])[0])
                except (TypeError, ValueError):
                    raise CaptureError("INVALID_WAIT_SECONDS")
                self._coordinator.begin(source_url, request_id)
                return self._json(200, self._coordinator.wait(request_id, wait_seconds))
        except (CaptureError, json.JSONDecodeError, ValueError) as exc:
            code = exc.code if isinstance(exc, CaptureError) else "INVALID_CAPTURE"
            status = {
                "FORBIDDEN_ORIGIN": 403,
                "CAPTURE_NOT_FOUND": 404,
                "CAPTURE_TIMEOUT": 408,
                "CAPTURE_BUSY": 409,
                "CAPTURE_CANCELLED": 409,
            }.get(code, 400)
            return self._json(status, {"status": "error", "error_code": code})
        return self._json(404, {"status": "error", "error_code": "NOT_FOUND"})


def capture_endpoint() -> str:
    value = os.getenv("BROWSER_CAPTURE_ENDPOINT", DEFAULT_CAPTURE_ENDPOINT)
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port != 18431
        or parsed.path != "/capture"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise CaptureError("INVALID_CAPTURE_CONFIGURATION")
    return value


def _read_token(token_file: Path) -> str:
    try:
        if token_file.stat().st_mode & 0o077:
            raise CaptureError("INSECURE_CAPTURE_TOKEN")
        token = token_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise CaptureError("CAPTURE_BRIDGE_UNAVAILABLE") from exc
    if not token:
        raise CaptureError("CAPTURE_BRIDGE_UNAVAILABLE")
    return token


def fetch_capture(
    source_url: str,
    *,
    client: httpx.Client | None = None,
    token: str | None = None,
    token_file: Path = DEFAULT_TOKEN_FILE,
    request_id: str | None = None,
    wait_seconds: float = 0,
) -> dict:
    _validate_source_url(source_url)
    bearer = token or _read_token(token_file)
    own_client = client is None
    if wait_seconds < 0 or wait_seconds > MAX_CAPTURE_WAIT_SECONDS:
        raise CaptureError("INVALID_WAIT_SECONDS")
    request_id = request_id or uuid.uuid4().hex
    client = client or httpx.Client(
        trust_env=False,
        timeout=httpx.Timeout(wait_seconds + 3, connect=1),
    )
    try:
        response = client.get(
            capture_endpoint(),
            params={
                "url": source_url,
                "request_id": request_id,
                "wait_seconds": str(wait_seconds),
            },
            headers={"Authorization": f"Bearer {bearer}", "Accept": "application/json"},
        )
        if response.status_code == 404:
            raise CaptureError("CAPTURE_NOT_FOUND")
        if response.status_code == 401:
            raise CaptureError("CAPTURE_UNAUTHORIZED")
        if response.status_code in (408, 409):
            raise CaptureError(response.json().get("error_code", "CAPTURE_BRIDGE_UNAVAILABLE"))
        response.raise_for_status()
        return normalize_capture(response.json())
    except CaptureError:
        raise
    except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
        raise CaptureError("CAPTURE_BRIDGE_UNAVAILABLE") from exc
    finally:
        if own_client:
            client.close()
