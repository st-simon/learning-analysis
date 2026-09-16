import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from browser_capture import (
    CaptureApplication,
    CaptureError,
    CaptureStore,
    capture_endpoint,
    fetch_capture,
    normalize_capture,
)


class CaptureContractTests(unittest.TestCase):
    def test_accepts_rendered_wechat_capture_without_persistence(self):
        payload = {
            "source_url": "https://mp.weixin.qq.com/s/example",
            "title": "测试文章",
            "markdown": "# 测试文章\n\n正文\n\n![图](https://mmbiz.qpic.cn/example)",
            "source_channel": "rendered_dom",
        }

        capture = normalize_capture(payload)

        self.assertEqual(capture["status"], "ok")
        self.assertEqual(capture["source_channel"], "rendered_dom")
        self.assertFalse(capture["network_used"])
        self.assertFalse(capture["persistent_write"])
        self.assertEqual(capture["characters"], len(payload["markdown"]))

    def test_rejects_non_wechat_or_unrendered_payload(self):
        invalid = [
            {"source_url": "https://example.com/a", "title": "x", "markdown": "body", "source_channel": "rendered_dom"},
            {"source_url": "https://mp.weixin.qq.com/s/a", "title": "x", "markdown": "", "source_channel": "rendered_dom"},
            {"source_url": "https://mp.weixin.qq.com/s/a", "title": "x", "markdown": "body", "source_channel": "reader"},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(CaptureError):
                normalize_capture(payload)

    def test_store_is_memory_only_and_url_scoped(self):
        store = CaptureStore()
        payload = normalize_capture({
            "source_url": "https://mp.weixin.qq.com/s/a",
            "title": "A",
            "markdown": "body",
            "source_channel": "rendered_dom",
        })

        store.put(payload)

        self.assertEqual(store.get(payload["source_url"])["title"], "A")
        with self.assertRaises(CaptureError):
            store.get("https://mp.weixin.qq.com/s/missing")


class CaptureApplicationTests(unittest.TestCase):
    def setUp(self):
        self.app = CaptureApplication(token="gate0-test-token")
        self.payload = json.dumps({
            "source_url": "https://mp.weixin.qq.com/s/a",
            "title": "A",
            "markdown": "body",
            "source_channel": "rendered_dom",
        }).encode()

    def test_extension_can_submit_and_authorized_mcp_can_read(self):
        status, _, body = self.app.handle(
            "POST", "/capture", {"origin": "chrome-extension://abcdefghijklmnop"}, self.payload
        )
        self.assertEqual(status, 202)
        self.assertNotIn(b"body", body)

        status, _, body = self.app.handle(
            "GET",
            "/capture?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2Fa",
            {"authorization": "Bearer gate0-test-token"},
            b"",
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["markdown"], "body")

    def test_web_page_cannot_submit_and_unauthorized_client_cannot_read(self):
        status, _, _ = self.app.handle(
            "POST", "/capture", {"origin": "https://mp.weixin.qq.com"}, self.payload
        )
        self.assertEqual(status, 403)

        status, _, body = self.app.handle(
            "GET", "/capture?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2Fa", {}, b""
        )
        self.assertEqual(status, 401)
        self.assertNotIn(b"body", body)


class CaptureClientTests(unittest.TestCase):
    def test_endpoint_is_fixed_to_loopback(self):
        self.assertEqual(capture_endpoint(), "http://127.0.0.1:18431/capture")
        with patch.dict("os.environ", {"BROWSER_CAPTURE_ENDPOINT": "https://example.com/capture"}):
            with self.assertRaises(CaptureError):
                capture_endpoint()

    def test_fetch_uses_local_token_and_returns_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "token"
            token_file.write_text("secret-token", encoding="utf-8")
            token_file.chmod(0o600)

            def handler(request):
                self.assertEqual(request.headers["authorization"], "Bearer secret-token")
                self.assertEqual(request.url.host, "127.0.0.1")
                return httpx.Response(200, json={
                    "status": "ok",
                    "source_channel": "rendered_dom",
                    "source_url": "https://mp.weixin.qq.com/s/a",
                    "title": "A",
                    "markdown": "body",
                    "characters": 4,
                    "network_used": False,
                    "persistent_write": False,
                    "warnings": [],
                    "limitations": "Rendered DOM only",
                })

            with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                result = fetch_capture(
                    "https://mp.weixin.qq.com/s/a", client=client, token_file=token_file
                )
            self.assertEqual(result["markdown"], "body")

    def test_fetch_classifies_missing_capture(self):
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(404, json={"error_code": "CAPTURE_NOT_FOUND"})
            )
        ) as client:
            with self.assertRaisesRegex(CaptureError, "CAPTURE_NOT_FOUND"):
                fetch_capture(
                    "https://mp.weixin.qq.com/s/a", client=client, token="secret-token"
                )


if __name__ == "__main__":
    unittest.main()
