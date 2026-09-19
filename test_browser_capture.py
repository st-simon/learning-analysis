import base64
import hashlib
import json
import os
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import server as mcp_server

from browser_capture import (
    CaptureApplication,
    CaptureCoordinator,
    CaptureError,
    CaptureStore,
    DEFAULT_EXTENSION_ID,
    normalize_capture,
)
from browser_capture_server import redacted_error_event
from capture_runtime import CaptureRuntime


EXTENSION_MANIFEST = (
    Path(__file__).resolve().parent
    / "extension"
    / "learning-analysis-capture"
    / "manifest.json"
)


class ExtensionIdentityTests(unittest.TestCase):
    def test_manifest_public_key_derives_expected_stable_extension_id(self):
        manifest = json.loads(EXTENSION_MANIFEST.read_text(encoding="utf-8"))
        digest = hashlib.sha256(base64.b64decode(manifest["key"])).digest()[:16]
        extension_id = "".join(
            chr(ord("a") + nibble)
            for byte in digest
            for nibble in (byte >> 4, byte & 0x0F)
        )

        self.assertEqual(extension_id, DEFAULT_EXTENSION_ID)
        self.assertEqual(manifest["permissions"], ["activeTab", "scripting"])
        self.assertEqual(manifest["host_permissions"], ["http://127.0.0.1:18431/*"])


class CaptureDiagnosticsTests(unittest.TestCase):
    def test_error_event_is_stage_only_and_suppresses_expected_poll_miss(self):
        self.assertIsNone(
            redacted_error_event(
                "GET",
                "/pending?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2Fsecret",
                404,
                b'{"status":"NO_PENDING"}',
            )
        )
        event = redacted_error_event(
            "GET",
            "/pending?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2Fsecret",
            403,
            b'{"status":"error","error_code":"FORBIDDEN_ORIGIN"}',
            headers={"Origin": "chrome-extension://other-extension"},
            allowed_origin="chrome-extension://expected-extension",
        )
        self.assertEqual(event, {
            "stage": "pending",
            "status": "error",
            "request_method": "GET",
            "http_status": 403,
            "error_code": "FORBIDDEN_ORIGIN",
            "origin_class": "OTHER_EXTENSION",
        })
        serialized = json.dumps(event)
        self.assertNotIn("mp.weixin", serialized)
        self.assertNotIn("secret", serialized)

    def test_origin_classification_does_not_log_origin_value(self):
        cases = [
            ({}, "MISSING"),
            ({"Origin": "chrome-extension://expected-extension"}, "EXACT"),
            ({"Origin": "chrome-extension://expected-extension/"}, "EXACT_TRAILING_SLASH"),
        ]
        for headers, expected in cases:
            with self.subTest(expected=expected):
                event = redacted_error_event(
                    "OPTIONS",
                    "/pending?url=redacted",
                    403,
                    b'{"status":"error","error_code":"FORBIDDEN_ORIGIN"}',
                    headers=headers,
                    allowed_origin="chrome-extension://expected-extension",
                )
                self.assertEqual(event["origin_class"], expected)
                self.assertNotIn("expected-extension", json.dumps(event))


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


class CaptureCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = CaptureCoordinator()

    @staticmethod
    def capture(source_url: str, title: str = "A") -> dict:
        return normalize_capture({
            "source_url": source_url,
            "title": title,
            "markdown": f"# {title}\n\nbody",
            "source_channel": "rendered_dom",
        })

    def test_wait_returns_capture_once_after_matching_accept(self):
        source_url = "https://mp.weixin.qq.com/s/a"
        self.coordinator.begin(source_url, "request-a")
        result = {}

        waiter = threading.Thread(
            target=lambda: result.update(self.coordinator.wait("request-a", 0.5))
        )
        waiter.start()
        time.sleep(0.02)
        self.coordinator.accept(self.capture(source_url))
        waiter.join(1)

        self.assertFalse(waiter.is_alive())
        self.assertEqual(result["title"], "A")
        with self.assertRaisesRegex(CaptureError, "CAPTURE_NOT_FOUND"):
            self.coordinator.wait("request-a", 0)

    def test_timeout_and_cancel_remove_pending_request(self):
        source_url = "https://mp.weixin.qq.com/s/a"
        self.coordinator.begin(source_url, "timeout")
        with self.assertRaisesRegex(CaptureError, "CAPTURE_TIMEOUT"):
            self.coordinator.wait("timeout", 0.01)
        with self.assertRaisesRegex(CaptureError, "CAPTURE_NOT_FOUND"):
            self.coordinator.accept(self.capture(source_url))

        self.coordinator.begin(source_url, "cancelled")
        self.coordinator.cancel("cancelled")
        with self.assertRaisesRegex(CaptureError, "CAPTURE_CANCELLED"):
            self.coordinator.wait("cancelled", 0)

    def test_concurrent_urls_are_isolated(self):
        url_a = "https://mp.weixin.qq.com/s/a"
        url_b = "https://mp.weixin.qq.com/s/b"
        self.coordinator.begin(url_a, "request-a")
        self.coordinator.begin(url_b, "request-b")
        self.coordinator.accept(self.capture(url_b, "B"))
        self.coordinator.accept(self.capture(url_a, "A"))

        self.assertEqual(self.coordinator.wait("request-a", 0)["title"], "A")
        self.assertEqual(self.coordinator.wait("request-b", 0)["title"], "B")

    def test_cancel_all_releases_every_waiter(self):
        errors = []
        for suffix in ("a", "b"):
            self.coordinator.begin(
                f"https://mp.weixin.qq.com/s/{suffix}", f"request-{suffix}"
            )
        waiters = [
            threading.Thread(
                target=lambda request_id=request_id: self._record_wait_error(
                    request_id, errors
                )
            )
            for request_id in ("request-a", "request-b")
        ]
        for waiter in waiters:
            waiter.start()

        self.coordinator.cancel_all()
        for waiter in waiters:
            waiter.join(1)

        self.assertEqual(errors, ["CAPTURE_CANCELLED", "CAPTURE_CANCELLED"])
        self.assertTrue(all(not waiter.is_alive() for waiter in waiters))

    def _record_wait_error(self, request_id: str, errors: list[str]) -> None:
        try:
            self.coordinator.wait(request_id, 0.5)
        except CaptureError as exc:
            errors.append(exc.code)


class CaptureApplicationTests(unittest.TestCase):
    def setUp(self):
        self.extension_id = "abcdefghijklmnopabcdefghijklmnop"
        self.origin = f"chrome-extension://{self.extension_id}"
        self.token = "gate1a-test-token"
        self.coordinator = CaptureCoordinator()
        self.app = CaptureApplication(
            token=self.token,
            extension_id=self.extension_id,
            coordinator=self.coordinator,
        )
        self.payload = json.dumps({
            "source_url": "https://mp.weixin.qq.com/s/a",
            "title": "A",
            "markdown": "body",
            "source_channel": "rendered_dom",
        }).encode()

    def test_extension_can_submit_and_authorized_mcp_can_read(self):
        self.coordinator.begin("https://mp.weixin.qq.com/s/a", "request-a")
        result = {}
        waiter = threading.Thread(
            target=lambda: result.update(
                {"capture": self.coordinator.wait("request-a", 0.5)}
            )
        )
        waiter.start()
        time.sleep(0.02)

        status, _, body = self.app.handle(
            "POST", "/capture",
            {"origin": self.origin, "authorization": f"Bearer {self.token}"},
            self.payload,
        )
        self.assertEqual(status, 202)
        self.assertNotIn(b"body", body)
        waiter.join(1)

        self.assertEqual(result["capture"]["markdown"], "body")

    def test_extension_can_observe_pending_before_extracting_article(self):
        pending_target = "/pending?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2Fa"
        headers = {
            "origin": self.origin,
            "authorization": f"Bearer {self.token}",
        }

        status, response_headers, body = self.app.handle(
            "GET", pending_target, headers, b""
        )
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body), {"status": "NO_PENDING"})
        self.assertEqual(response_headers["Access-Control-Allow-Origin"], self.origin)

        self.app._coordinator.begin("https://mp.weixin.qq.com/s/a", "request-a")
        status, response_headers, body = self.app.handle(
            "GET", pending_target, headers, b""
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "PENDING_READY"})
        self.assertEqual(response_headers["Access-Control-Allow-Origin"], self.origin)

    def test_web_page_cannot_submit_and_unauthorized_client_cannot_read(self):
        status, _, _ = self.app.handle(
            "POST", "/capture", {"origin": "https://mp.weixin.qq.com"}, self.payload
        )
        self.assertEqual(status, 403)


    def test_wrong_extension_or_install_token_cannot_submit(self):
        status, _, body = self.app.handle(
            "POST",
            "/capture",
            {"origin": "chrome-extension://ponmlkjihgfedcbaponmlkjihgfedcba", "authorization": f"Bearer {self.token}"},
            self.payload,
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error_code"], "FORBIDDEN_ORIGIN")

        status, _, body = self.app.handle(
            "POST",
            "/capture",
            {"origin": self.origin, "authorization": "Bearer wrong-token"},
            self.payload,
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error_code"], "UNAUTHORIZED")

    def test_pending_readiness_rejects_wrong_origin_token_and_url(self):
        pending_target = "/pending?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2Fa"

        status, _, body = self.app.handle(
            "GET",
            pending_target,
            {
                "origin": "chrome-extension://ponmlkjihgfedcbaponmlkjihgfedcba",
                "authorization": f"Bearer {self.token}",
            },
            b"",
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error_code"], "FORBIDDEN_ORIGIN")

        status, _, body = self.app.handle(
            "GET",
            pending_target,
            {"origin": self.origin, "authorization": "Bearer wrong-token"},
            b"",
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error_code"], "UNAUTHORIZED")

        status, _, body = self.app.handle(
            "GET",
            "/pending?url=https%3A%2F%2Fexample.com%2Fs%2Fa",
            {
                "origin": self.origin,
                "authorization": f"Bearer {self.token}",
            },
            b"",
        )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error_code"], "INVALID_SOURCE_URL")

    def test_pending_readiness_does_not_expose_request_or_article_data(self):
        self.app._coordinator.begin("https://mp.weixin.qq.com/s/a", "secret-request")
        status, _, body = self.app.handle(
            "GET",
            "/pending?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2Fa",
            {
                "origin": self.origin,
                "authorization": f"Bearer {self.token}",
            },
            b"",
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"status": "PENDING_READY"}')
        self.assertNotIn(b"secret-request", body)
        self.assertNotIn(b"mp.weixin.qq.com", body)

    def test_missing_origin_requires_exact_extension_id_header_and_token(self):
        pending_target = "/pending?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2Fa"
        base_headers = {"authorization": f"Bearer {self.token}"}

        for extension_id in (None, "ponmlkjihgfedcbaponmlkjihgfedcba"):
            headers = dict(base_headers)
            if extension_id is not None:
                headers["x-learning-analysis-extension-id"] = extension_id
            status, _, body = self.app.handle(
                "GET", pending_target, headers, b""
            )
            self.assertEqual(status, 403)
            self.assertEqual(json.loads(body)["error_code"], "FORBIDDEN_EXTENSION")

        status, _, body = self.app.handle(
            "GET",
            pending_target,
            {
                **base_headers,
                "origin": "https://mp.weixin.qq.com",
                "x-learning-analysis-extension-id": self.extension_id,
            },
            b"",
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error_code"], "FORBIDDEN_ORIGIN")

        self.app._coordinator.begin("https://mp.weixin.qq.com/s/a", "request-a")
        status, _, body = self.app.handle(
            "GET",
            pending_target,
            {
                **base_headers,
                "x-learning-analysis-extension-id": self.extension_id,
            },
            b"",
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "PENDING_READY"})

    def test_missing_origin_extension_can_submit_with_exact_id_header(self):
        self.app._coordinator.begin("https://mp.weixin.qq.com/s/a", "request-a")
        status, _, body = self.app.handle(
            "POST",
            "/capture",
            {
                "authorization": f"Bearer {self.token}",
                "x-learning-analysis-extension-id": self.extension_id,
            },
            self.payload,
        )
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body)["status"], "accepted")


@unittest.skipUnless(
    os.getenv("RUN_LOOPBACK_INTEGRATION") == "1",
    "set RUN_LOOPBACK_INTEGRATION=1 to bind a real loopback socket",
)
class CaptureRuntimeTests(unittest.TestCase):
    def test_stop_cancels_in_flight_capture_wait(self):
        runtime = CaptureRuntime(token="runtime-stop-token", port=0)
        errors = []
        runtime.start()
        waiter = threading.Thread(
            target=lambda: self._record_runtime_error(runtime, errors)
        )
        waiter.start()
        time.sleep(0.02)

        runtime.stop()
        waiter.join(1)

        self.assertEqual(errors, ["CAPTURE_CANCELLED"])
        self.assertFalse(waiter.is_alive())

    @staticmethod
    def _record_runtime_error(runtime: CaptureRuntime, errors: list[str]) -> None:
        try:
            runtime.request_capture(
                "https://mp.weixin.qq.com/s/a",
                request_id="runtime-stop",
                timeout=0.5,
            )
        except CaptureError as exc:
            errors.append(exc.code)

    def test_shared_runtime_wait_is_completed_by_exact_loopback_extension(self):
        extension_id = "abcdefghijklmnopabcdefghijklmnop"
        token = "runtime-integration-token"
        runtime = CaptureRuntime(token=token, extension_id=extension_id, port=0)
        result = {}
        runtime.start()
        waiter = threading.Thread(target=lambda: result.update({
            "capture": runtime.request_capture(
                "https://mp.weixin.qq.com/s/a",
                request_id="runtime-a",
                timeout=0.5,
            )
        }))
        waiter.start()

        try:
            client = httpx.Client(trust_env=False, timeout=1)
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Learning-Analysis-Extension-Id": extension_id,
            }
            deadline = time.monotonic() + 0.5
            while True:
                pending = client.get(
                    f"{runtime.base_url}/pending",
                    params={"url": "https://mp.weixin.qq.com/s/a"},
                    headers=headers,
                )
                if pending.status_code == 200 or time.monotonic() >= deadline:
                    break
                time.sleep(0.01)
            submitted = client.post(
                f"{runtime.base_url}/capture",
                headers=headers,
                json={
                    "source_url": "https://mp.weixin.qq.com/s/a",
                    "title": "A",
                    "markdown": "body",
                    "source_channel": "rendered_dom",
                },
            )
            waiter.join(1)

            self.assertEqual(pending.json(), {"status": "PENDING_READY"})
            self.assertEqual(submitted.status_code, 202)
            self.assertFalse(waiter.is_alive())
            self.assertEqual(result["capture"]["title"], "A")
            self.assertEqual(runtime.health(), {"status": "ok", "ready": True})
        finally:
            client.close()
            runtime.stop()

        self.assertEqual(runtime.health(), {"status": "stopped", "ready": False})


class CaptureToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_rendered_tool_requests_capture_directly_from_shared_runtime(self):
        class FakeRuntime:
            def __init__(self):
                self.calls = []

            def request_capture(self, source_url, *, request_id, timeout):
                self.calls.append((source_url, request_id, timeout))
                return {
                    "status": "ok",
                    "source_channel": "rendered_dom",
                    "source_url": source_url,
                    "title": "A",
                    "markdown": "body",
                    "characters": 4,
                    "network_used": False,
                    "persistent_write": False,
                    "warnings": [],
                    "limitations": "Rendered DOM only",
                }

        runtime = FakeRuntime()
        with patch.object(mcp_server, "_capture_runtime", runtime):
            result = await mcp_server.read_rendered_url(
                "https://mp.weixin.qq.com/s/a"
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["title"], "A")
        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.calls[0][0], "https://mp.weixin.qq.com/s/a")
        self.assertEqual(runtime.calls[0][2], 25)


if __name__ == "__main__":
    unittest.main()
