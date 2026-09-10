import hashlib, ipaddress, json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import httpx

ROOT = Path(__file__).resolve().parent
ALLOWED = frozenset(os.getenv("READER_ALLOWED_HOSTS", "example.com,www.iana.org,mp.weixin.qq.com").split(","))
MAX_RESPONSE = 4_000_000

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

def read_article(url, *, client=None, archive_dir=None):
    validate_url(url)
    own = client is None
    client = client or httpx.Client(trust_env=False, timeout=httpx.Timeout(45, connect=5))
    try:
        with client.stream("POST", "http://127.0.0.1:17831/", json={"url": url, "respondWith": "markdown", "assertStatusCode": 200}, headers={"Accept": "application/json"}) as r:
            r.raise_for_status(); body = bytearray()
            for block in r.iter_bytes():
                body.extend(block)
                if len(body) > MAX_RESPONSE: raise ValueError("Article exceeds response limit")
        payload = json.loads(body); data = payload.get("data")
        if not isinstance(data, dict): raise ValueError("Reader did not return a successful article")
        content = data.get("content")
        if not isinstance(content, str) or not content.strip(): raise ValueError("Reader returned empty article text")
        title, source = str(data.get("title") or "Untitled"), str(data.get("url") or url)
        warning = str(data.get("warning") or payload.get("warning") or "")
        if "captcha" in (warning + title).lower(): raise ValueError("Reader reported a CAPTCHA")
        path = archive(content, source, title, archive_dir or ROOT / "archive")
        return {"title": title, "source_url": source, "markdown": content, "characters": len(content), "saved_file": str(path), "warnings": warning, "limitations": "Image text is not OCRed; extraction may omit inaccessible content."}
    finally:
        if own: client.close()
