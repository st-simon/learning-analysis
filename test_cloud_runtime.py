import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

import server
from http_server import PinnedTokenVerifier, create_app, from_environment
from reader import ReaderError, read_article, validate_public_dns


class ReaderCloudTests(unittest.TestCase):
    def client(self, payload):
        return httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)))

    def test_no_archive_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmp, self.client({"data": {"content": "正文"}}) as client:
            target = Path(tmp) / "archive"
            result = read_article("https://example.com", client=client, persist=False, archive_dir=target)
            self.assertIsNone(result["saved_file"])
            self.assertIsNone(result["archive_id"])
            self.assertFalse(target.exists())

    def test_rejects_unsafe_resolved_address(self):
        with patch("reader.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("169.254.169.254", 443))]):
            with self.assertRaisesRegex(ReaderError, "UNSAFE_DESTINATION"):
                validate_public_dns("https://example.com")

    def test_rejects_unallowed_returned_source(self):
        with self.client({"data": {"content": "x", "url": "http://127.0.0.1"}}) as client:
            with self.assertRaises(ValueError):
                read_article("https://example.com", client=client, persist=False)

    def test_chinese_access_restriction(self):
        with self.client({"data": {"content": "x", "title": "环境异常"}}) as client:
            with self.assertRaisesRegex(ReaderError, "ACCESS_RESTRICTED"):
                read_article("https://example.com", client=client, persist=False)

    def test_cloud_requires_no_archive(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                from_environment()


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_kills_worker_and_releases_slot(self):
        class Process:
            returncode = None
            killed = False
            async def communicate(self, _input):
                await asyncio.sleep(10)
            def kill(self):
                self.killed = True
                self.returncode = -9
            async def wait(self):
                return self.returncode
        process = Process()
        with patch("server.asyncio.create_subprocess_exec", AsyncMock(return_value=process)), patch("server.REQUEST_DEADLINE", 0.01):
            result = await server.read_url("https://example.com")
        self.assertEqual(result["error_code"], "READ_TIMEOUT")
        self.assertTrue(process.killed)
        self.assertFalse(server._busy)

    async def test_busy_rejects_without_worker(self):
        with patch("server._busy", True), patch("server.asyncio.create_subprocess_exec", AsyncMock()) as spawn:
            result = await server.read_url("https://example.com")
            self.assertEqual(result["error_code"], "BUSY")
            spawn.assert_not_called()


class HTTPAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        public.update(kid="test", alg="RS256", use="sig")
        cls.jwks = {"keys": [public]}

    def token(self, **changes):
        claims = dict(iss="https://issuer.example", aud="https://reader.example/mcp",
                      sub="owner", iat=int(time.time()), exp=int(time.time()) + 300,
                      scope="articles:read")
        claims.update(changes)
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "test"})

    def app(self):
        return create_app(issuer="https://issuer.example", resource="https://reader.example/mcp",
                          jwks=self.jwks, subjects=["owner"])

    def test_rejects_bad_claims(self):
        verifier = PinnedTokenVerifier("https://issuer.example", "https://reader.example/mcp", self.jwks, ["owner"])
        for changes in ({"aud": "elsewhere"}, {"iss": "elsewhere"}, {"exp": 1}, {"sub": "stranger"}, {"scope": "other"}):
            with self.subTest(changes=changes):
                self.assertIsNone(asyncio.run(verifier.verify_token(self.token(**changes))))
        self.assertIsNotNone(asyncio.run(verifier.verify_token(self.token())))

    def test_anonymous_request_challenged(self):
        with TestClient(self.app(), base_url="https://reader.example") as client:
            response = client.post("/mcp", json={})
            self.assertEqual(response.status_code, 401)
            self.assertIn("resource_metadata", response.headers["www-authenticate"])
            metadata = client.get("/.well-known/oauth-protected-resource/mcp")
            self.assertEqual(metadata.status_code, 200)
            self.assertEqual(metadata.json()["resource"], "https://reader.example/mcp")

    def test_stateless_initialize_and_list_tools(self):
        with TestClient(self.app(), base_url="https://reader.example") as client:
            headers = {"Authorization": "Bearer " + self.token(),
                       "Accept": "application/json, text/event-stream"}
            response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1,
                "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"}}})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("mcp-session-id", response.headers)
            response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["result"]["tools"][0]["name"], "read_url")


if __name__ == "__main__":
    unittest.main()
