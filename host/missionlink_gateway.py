"""Loopback-only HTTP bridge for authenticated local MissionLink clients.

This is a local development boundary, not a production remote gateway:
- binds only to an explicit loopback IP address;
- requires per-client bearer tokens mapped to dispatcher principals;
- never logs request headers or payloads;
- limits request bodies to the service-envelope wire ceiling;
- returns sanitized service metadata without endpoint URLs.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import ipaddress
import json
import time
from collections.abc import Mapping
from typing import Any

from host.missionlink_dispatch import DispatchError, ServiceDispatcher
from host.missionlink_envelopes import MAX_ENVELOPE_BYTES, EnvelopeError
from host.missionlink_services import ServiceRegistry

MAX_HTTP_BODY_BYTES = MAX_ENVELOPE_BYTES
MAX_TOKEN_COUNT = 64


class GatewayConfigurationError(ValueError):
    """Raised when the local gateway would violate its security boundary."""


def _validate_tokens(tokens: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(tokens, Mapping) or not tokens or len(tokens) > MAX_TOKEN_COUNT:
        raise GatewayConfigurationError("invalid_token_map")
    clean: dict[str, str] = {}
    for token, principal in tokens.items():
        if not isinstance(token, str) or len(token) < 32 or len(token) > 256:
            raise GatewayConfigurationError("token_must_be_32_to_256_characters")
        if not isinstance(principal, str) or not principal or len(principal) > 64:
            raise GatewayConfigurationError("invalid_principal")
        if token in clean:
            raise GatewayConfigurationError("duplicate_token")
        clean[token] = principal
    return clean


def _loopback_address(host: str) -> str:
    if not isinstance(host, str):
        raise GatewayConfigurationError("loopback_bind_required")
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        # Do not rely on hostname resolution for a security boundary.
        raise GatewayConfigurationError("bind_must_be_loopback_ip_literal") from exc
    # ThreadingHTTPServer uses IPv4 by default; reject IPv6 instead of failing at startup.
    if address.version != 4 or not address.is_loopback:
        raise GatewayConfigurationError("bind_must_be_ipv4_loopback")
    return str(address)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def make_handler(dispatcher: ServiceDispatcher, registry: ServiceRegistry,
                 bearer_tokens: Mapping[str, str]) -> type[BaseHTTPRequestHandler]:
    if not isinstance(dispatcher, ServiceDispatcher) or not isinstance(registry, ServiceRegistry):
        raise GatewayConfigurationError("dispatcher_and_registry_required")
    tokens = _validate_tokens(bearer_tokens)

    class GatewayHandler(BaseHTTPRequestHandler):
        server_version = "MissionLinkGateway/0.1"
        sys_version = ""

        def log_message(self, format: str, *args: Any) -> None:
            # Default HTTP logging can include paths and client-supplied text.
            # Keep credentials, payloads, and request details out of logs.
            return

        def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: int, code: str) -> None:
            self._send(status, _json_bytes({"error": code}))

        def _principal(self) -> str | None:
            header = self.headers.get("Authorization", "")
            prefix = "Bearer "
            if not header.startswith(prefix):
                return None
            supplied = header[len(prefix):]
            matched: str | None = None
            # Compare against every configured token rather than short-circuiting
            # on the first matching token.
            for token, principal in tokens.items():
                if hmac.compare_digest(supplied.encode("utf-8"), token.encode("utf-8")):
                    matched = principal
            return matched

        def _authorized_principal(self) -> str | None:
            return self._principal()

        def do_GET(self) -> None:
            principal = self._authorized_principal()
            if principal is None:
                self._error(401, "unauthorized")
                return
            if self.path != "/v1/services":
                self._error(404, "not_found")
                return
            records = []
            for record in registry.list(healthy_only=True):
                records.append({
                    "serviceId": record.service_id,
                    "hostId": record.host_id,
                    "displayName": record.display_name,
                    "capabilities": list(record.capabilities),
                    "transports": list(record.transports),
                    "healthy": record.healthy,
                    "maxInlineRequestBytes": record.max_inline_request_bytes,
                })
            self._send(200, _json_bytes({"schemaVersion": 1, "services": records}))

        def do_POST(self) -> None:
            principal = self._authorized_principal()
            if principal is None:
                self._error(401, "unauthorized")
                return
            if self.path != "/v1/dispatch":
                self._error(404, "not_found")
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                self._error(415, "unsupported_media_type")
                return
            raw_length = self.headers.get("Content-Length")
            try:
                length = int(raw_length) if raw_length is not None else -1
            except ValueError:
                length = -1
            if length < 1:
                self._error(400, "invalid_content_length")
                return
            if length > MAX_HTTP_BODY_BYTES:
                self._error(413, "request_too_large")
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                self._error(400, "incomplete_body")
                return
            now_ms = time.time_ns() // 1_000_000
            try:
                response = dispatcher.dispatch(raw, principal_id=principal, now_ms=now_ms)
                response_bytes = response.to_bytes()
            except DispatchError as exc:
                status = 403 if exc.code == "forbidden" else 400
                if exc.code in ("not_found", "operation_not_found"):
                    status = 404
                elif exc.code == "unavailable":
                    status = 503
                elif exc.code in ("too_large", "response_too_large"):
                    status = 413
                elif exc.code == "replay_cache_full":
                    status = 429
                self._error(status, exc.code)
                return
            except EnvelopeError:
                self._error(500, "response_encoding_failed")
                return
            self._send(200, response_bytes)

    return GatewayHandler


def create_gateway_server(host: str, port: int, dispatcher: ServiceDispatcher,
                          registry: ServiceRegistry,
                          bearer_tokens: Mapping[str, str]) -> ThreadingHTTPServer:
    """Create, but do not start, a local server bound to a loopback IP only."""
    bind_host = _loopback_address(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise GatewayConfigurationError("invalid_port")
    handler = make_handler(dispatcher, registry, bearer_tokens)
    server = ThreadingHTTPServer((bind_host, port), handler)
    server.daemon_threads = True
    return server
