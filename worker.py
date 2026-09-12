"""One read per process, enabling a hard deadline without orphaned HTTP reads."""
import json
import socket
import sys
import httpx
from reader import ReaderError, read_article

def execute(url):
    try:
        return {"status": "ok", **read_article(url)}
    except ReaderError as exc:
        code = exc.code
    except (httpx.TimeoutException, TimeoutError):
        code = "READ_TIMEOUT"
    except (httpx.ConnectError, socket.gaierror):
        code = "READER_UNREACHABLE"
    except httpx.HTTPError:
        code = "READER_HTTP_ERROR"
    except (ValueError, TypeError):
        code = "INVALID_REQUEST_OR_RESPONSE"
    except Exception:
        code = "INTERNAL_ERROR"
    return {"status": "error", "error_code": code,
            "message": "Article could not be read. No automatic retry."}

if __name__ == "__main__":
    request = json.load(sys.stdin)
    print(json.dumps(execute(request["url"]), ensure_ascii=False))
