import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from host.missionlink_dispatch import ServiceDispatcher
from host.missionlink_envelopes import ServiceEnvelope
from host.missionlink_gateway import (
    GatewayConfigurationError,
    create_gateway_server,
)
from host.missionlink_services import ServiceRecord, ServiceRegistry

NOW = 10_000
TOKEN = "local-test-token-" + ("x" * 40)
BLOCKED_TOKEN = "blocked-test-token-" + ("y" * 40)


def setup_gateway():
    registry = ServiceRegistry()
    registry.register(ServiceRecord(
        service_id="weather.local",
        host_id="weather.node",
        display_name="Weather",
        capabilities=("weather.current",),
        transports=("lan",),
        endpoint="http://127.0.0.1:9000/private",
        max_inline_request_bytes=64,
    ))
    dispatcher = ServiceDispatcher(
        registry, {"local-client": frozenset({"weather.local"})}
    )
    dispatcher.register_handler(
        "weather.local", "weather.current",
        lambda principal, payload: {"ok": True, "principal": principal},
    )
    server = create_gateway_server(
        "127.0.0.1", 0, dispatcher, registry, {TOKEN: "local-client", BLOCKED_TOKEN: "blocked-client"}
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def http_call(url, *, method="GET", token=TOKEN, body=None, content_type="application/json"):
    headers = {}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = content_type
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, response.read(), response.headers
    except HTTPError as exc:
        return exc.code, exc.read(), exc.headers


class LocalGatewayTests(unittest.TestCase):
    def setUp(self):
        self.server, self.thread, self.base = setup_gateway()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_gateway_rejects_non_loopback_bind_addresses(self):
        for host in ("0.0.0.0", "192.168.1.20", "localhost"):
            with self.subTest(host=host), self.assertRaises(GatewayConfigurationError):
                create_gateway_server(host, 0, None, None, {TOKEN: "local-client"})

    def test_gateway_rejects_weak_or_empty_token_configuration(self):
        registry = ServiceRegistry()
        dispatcher = ServiceDispatcher(registry, {"local-client": frozenset()})
        for tokens in ({}, {"short": "local-client"}):
            with self.subTest(tokens=tokens), self.assertRaises(GatewayConfigurationError):
                create_gateway_server("127.0.0.1", 0, dispatcher, registry, tokens)

    def test_authentication_is_required_for_service_discovery(self):
        status, body, headers = http_call(self.base + "/v1/services", token=None)
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body), {"error": "unauthorized"})
        self.assertEqual(headers.get("Cache-Control"), "no-store")

    def test_service_discovery_is_sanitized(self):
        status, body, _ = http_call(self.base + "/v1/services")
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["schemaVersion"], 1)
        self.assertEqual(result["services"][0]["serviceId"], "weather.local")
        self.assertNotIn("endpoint", result["services"][0])
        self.assertNotIn("private", body.decode("utf-8"))

    def _request_envelope(self, request_id="gateway-1", *, created_at_ms=None, expires_at_ms=None):
        import time
        now_ms = time.time_ns() // 1_000_000
        created = now_ms if created_at_ms is None else created_at_ms
        expires = created + 20_000 if expires_at_ms is None else expires_at_ms
        return ServiceEnvelope(
            kind="request", request_id=request_id, service_id="weather.local",
            operation="weather.current", created_at_ms=created,
            expires_at_ms=expires, payload={"units": "metric"},
        ).to_bytes()

    def test_dispatch_returns_correlated_response_and_uses_token_principal(self):
        raw = self._request_envelope()
        status, body, _ = http_call(self.base + "/v1/dispatch", method="POST", body=raw)
        self.assertEqual(status, 200)
        response = ServiceEnvelope.from_bytes(body)
        self.assertEqual(response.kind, "response")
        self.assertEqual(response.request_id, "gateway-1")
        self.assertEqual(response.payload, {"ok": True, "principal": "local-client"})


    def test_dispatch_requires_token_and_rejects_principal_without_service_acl(self):
        raw = self._request_envelope()
        status, body, _ = http_call(
            self.base + "/v1/dispatch", method="POST", token=None, body=raw
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body), {"error": "unauthorized"})

        status, body, _ = http_call(
            self.base + "/v1/dispatch", method="POST", token=BLOCKED_TOKEN, body=raw
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body), {"error": "forbidden"})

    def test_dispatch_rejects_malformed_and_expired_envelopes(self):
        status, body, _ = http_call(
            self.base + "/v1/dispatch", method="POST", body=b"{not-json"
        )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body), {"error": "bad_request"})

        import time
        now_ms = time.time_ns() // 1_000_000
        raw = self._request_envelope(
            "expired-1", created_at_ms=now_ms - 60_000, expires_at_ms=now_ms - 1
        )
        status, body, _ = http_call(
            self.base + "/v1/dispatch", method="POST", body=raw
        )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body), {"error": "expired"})

    def test_dispatch_replay_is_rejected_without_second_handler_execution(self):
        raw = self._request_envelope("once-only")
        status, body, _ = http_call(
            self.base + "/v1/dispatch", method="POST", body=raw
        )
        self.assertEqual(status, 200)
        status, body, _ = http_call(
            self.base + "/v1/dispatch", method="POST", body=raw
        )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body), {"error": "replay"})

    def test_invalid_media_type_and_oversized_body_are_rejected(self):
        status, body, _ = http_call(
            self.base + "/v1/dispatch", method="POST", body=b"{}", content_type="text/plain"
        )
        self.assertEqual(status, 415)
        self.assertEqual(json.loads(body)["error"], "unsupported_media_type")
        status, body, _ = http_call(
            self.base + "/v1/dispatch", method="POST", body=b"x" * 181
        )
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(body)["error"], "request_too_large")

    def test_unknown_routes_are_not_exposed(self):
        status, body, _ = http_call(self.base + "/")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
