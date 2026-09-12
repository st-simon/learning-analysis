"""Stateless MCP resource server. OAuth issuer setup is external to this service."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import jwt
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse

from server import read_url


class PinnedTokenVerifier:
    """Verify using an operator-provided PUBLIC JWKS, never token-supplied URLs.

    Rotation requires replacing the public JWKS configuration and a new revision.
    An explicit subject allowlist keeps this deployment private to its owner.
    """

    def __init__(self, issuer, resource, jwks, subjects):
        if not subjects:
            raise ValueError("An owner subject allowlist is required")
        self.issuer, self.resource, self.subjects = issuer, resource, set(subjects)
        self.keys = {}
        for key in jwks["keys"]:
            if key.get("kty") != "RSA" or key.get("use", "sig") != "sig":
                continue
            if key.get("alg", "RS256") != "RS256" or "d" in key:
                raise ValueError("Only public RS256 verification keys are accepted")
            kid = key.get("kid")
            if not kid or kid in self.keys:
                raise ValueError("Verification keys need unique kid values")
            self.keys[kid] = jwt.PyJWK.from_dict(key).key
        if not self.keys:
            raise ValueError("No public RS256 verification keys configured")

    async def verify_token(self, token):
        if len(token) > 16384:
            return None
        try:
            header = jwt.get_unverified_header(token)
            key = self.keys.get(header.get("kid"))
            if key is None or header.get("alg") != "RS256":
                return None
            claims = jwt.decode(
                token, key, algorithms=["RS256"], issuer=self.issuer,
                audience=self.resource,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]})
            if claims["sub"] not in self.subjects:
                return None
            scope = claims.get("scope", "")
            if not isinstance(scope, str) or "articles:read" not in scope.split():
                return None
            return AccessToken(token=token, client_id=str(claims.get("client_id", claims["sub"])),
                               scopes=scope.split(), expires_at=int(claims["exp"]),
                               resource=self.resource, subject=claims["sub"])
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            return None


def https_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
            parsed.password or parsed.query or parsed.fragment or parsed.port not in (None, 443)):
        raise ValueError("Canonical HTTPS URL required")
    return value


def create_app(*, issuer, resource, jwks, subjects):
    issuer, resource = https_url(issuer), https_url(resource)
    host = urlsplit(resource).netloc
    origin = "https://" + host
    service = FastMCP(
        "learning-analysis", stateless_http=True, json_response=True,
        max_request_body_size=32768,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[host], allowed_origins=[origin]),
        auth=AuthSettings(issuer_url=issuer, resource_server_url=resource,
                          required_scopes=["articles:read"], validate_token_resource=True),
        token_verifier=PinnedTokenVerifier(issuer, resource, jwks, subjects))
    service.add_tool(read_url, name="read_url",
                     description="Read an allowed public article. No automatic retry; cloud mode does not archive text.",
                     annotations=ToolAnnotations(
                         readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True))

    @service.custom_route("/healthz", methods=["GET"])
    async def health(_request):
        # Process health only; this does not claim Reader or OAuth is reachable.
        return JSONResponse({"status": "alive", "reader_verified": False})

    return service.streamable_http_app()


def from_environment():
    if os.environ.get("READER_ARCHIVE_MODE") != "none":
        raise ValueError("HTTP cloud mode requires READER_ARCHIVE_MODE=none")
    return create_app(
        issuer=os.environ["MCP_ISSUER_URL"], resource=os.environ["MCP_RESOURCE_URL"],
        jwks=json.loads(Path(os.environ["MCP_PUBLIC_JWKS_FILE"]).read_text()),
        subjects=[s.strip() for s in os.environ["MCP_OWNER_SUBJECTS"].split(",") if s.strip()])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(from_environment(), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")),
                access_log=False)
