import hashlib, ipaddress, json, os, tempfile, socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import httpx

ROOT = Path(__file__).resolve().parent
ALLOWED = frozenset(os.getenv("READER_ALLOWED_HOSTS", "example.com,www.iana.org,mp.weixin.qq.com").split(","))
MAX_RESPONSE = 4_000_000

class ReaderError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code

def validate_public_dns(url):
    addresses = socket.getaddrinfo(urlsplit(url).hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ReaderError("UNSAFE_DESTINATION")

def reader_endpoint():
    value = os.getenv("READER_ENDPOINT", "http://127.0.0.1:17831/")
    p = urlsplit(value)
    if p.scheme != "http" or p.hostname != "127.0.0.1" or p.username or p.password or p.query or p.fragment or p.path not in ("", "/"):
        raise ReaderError("INVALID_CONFIGURATION")
    return value

def validate_url(url: str) -> str:
    p = urlsplit(url)
    if len(url) > 8192 or any(ord(c) < 32 or c.isspace() for c in url) or p.scheme != "https" or p.username or p.password or p.port not in (None, 443) or p.hostname not in ALLOWED:
        raise ValueError("Use an HTTPS URL on an explicitly allowed host; credentials and custom ports are forbidden")
    try:
        literal = ipaddress.ip_address(p.hostname)
    except ValueError:
        literal = None
    if literal is not None and not literal.is_global:
        raise ValueError("Target must resolve only to public addresses")
    return url

def archive(markdown, source, title, directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (hashlib.sha256((source + "\n" + markdown).encode()).hexdigest() + ".md")
    if not path.exists():
        fd, name = tempfile.mkstemp(dir=directory, prefix=".reader-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("---\ntitle: " + json.dumps(title, ensure_ascii=False) + "\nsource: " + json.dumps(source, ensure_ascii=False) + "\nfetched_at: " + datetime.now(timezone.utc).isoformat() + "\n---\n\n" + markdown)
            os.replace(name, path)
        finally:
            if os.path.exists(name): os.unlink(name)
    return path

def read_article(url, *, client=None, archive_dir=None, persist=None):
    validate_url(url)
    own = client is None
    # Admission check only: Reader's actual egress requires network enforcement.
    if own:
        validate_public_dns(url)
    mode = os.getenv("READER_ARCHIVE_MODE", "local")
    if mode not in ("local", "none"):
        raise ReaderError("INVALID_CONFIGURATION")
    persist = mode == "local" if persist is None else persist
    endpoint = reader_endpoint()
    client = client or httpx.Client(trust_env=False, timeout=httpx.Timeout(45, connect=5))
    try:
        with client.stream("POST", endpoint, json={"url": url, "respondWith": "markdown", "assertStatusCode": 200}, headers={"Accept": "application/json"}) as r:
            if r.status_code in (401, 403, 429): raise ReaderError("ACCESS_RESTRICTED")
            r.raise_for_status(); body = bytearray()
            for block in r.iter_bytes():
                body.extend(block)
                if len(body) > MAX_RESPONSE: raise ReaderError("RESPONSE_TOO_LARGE")
        payload = json.loads(body)
        if not isinstance(payload, dict): raise ReaderError("INVALID_RESPONSE")
        data = payload.get("data")
        if not isinstance(data, dict): raise ReaderError("INVALID_RESPONSE")
        content = data.get("content")
        if not isinstance(content, str) or not content.strip(): raise ReaderError("EMPTY_ARTICLE")
        title, source = str(data.get("title") or "Untitled"), str(data.get("url") or url)
        warning = str(data.get("warning") or payload.get("warning") or "")
        if any(word in (warning + title).lower() for word in ("captcha", "验证码", "访问受限", "环境异常")):
            raise ReaderError("ACCESS_RESTRICTED")
        validate_url(source)
        path = None
        if persist:
            try: path = archive(content, source, title, archive_dir or ROOT / "archive")
            except OSError: raise ReaderError("ARCHIVE_FAILED") from None
        return {"title": title, "source_url": source, "markdown": content, "characters": len(content), "saved_file": str(path) if path else None, "archive_id": path.stem if path else None, "warnings": warning, "limitations": "Image text is not OCRed; extraction may omit inaccessible content."}
    finally:
        if own: client.close()
