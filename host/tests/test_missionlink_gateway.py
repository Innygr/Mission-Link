import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from host.missionlink_gateway import LoopbackGatewayServer
from host.missionlink_services import ServiceRegistry


TOKEN = "test-token-that-is-long-enough-for-the-gateway"


class LoopbackGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = ServiceRegistry()
        cls.server = LoopbackGatewayServer(("127.0.0.1", 0), cls.registry, TOKEN)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method="GET", path="/v1/services", payload=None, token=TOKEN):
        headers = {}
        data = None
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=2)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def test_health_is_available_without_auth_and_has_no_registry_data(self):
        status, body = self.request(path="/v1/health", token=None)
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "api_version": 1})

    def test_services_require_token(self):
        status, body = self.request(token=None)
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "unauthorized")

    def test_register_list_get_and_delete(self):
        record = {
            "service_id": "ai.local",
            "host_id": "workstation",
            "display_name": "Local AI",
            "capabilities": ["ai.inference"],
        }
        status, body = self.request("POST", payload=record)
        self.assertEqual(status, 201)
        self.assertEqual(body["service"]["service_id"], "ai.local")

        status, body = self.request(path="/v1/services?capability=ai.inference")
        self.assertEqual(status, 200)
        self.assertEqual([x["service_id"] for x in body["services"]], ["ai.local"])

        status, body = self.request(path="/v1/services/ai.local")
        self.assertEqual(status, 200)
        self.assertEqual(body["service"]["host_id"], "workstation")

        status, body = self.request("DELETE", "/v1/services/ai.local")
        self.assertEqual(status, 200)
        self.assertEqual(body["removed"], "ai.local")

    def test_invalid_records_and_unknown_fields_rejected(self):
        for payload in (
            {"service_id": "../x", "host_id": "host", "display_name": "x", "capabilities": ["read"]},
            {"service_id": "ok", "host_id": "host", "display_name": "x", "capabilities": ["read"], "execute": True},
        ):
            with self.subTest(payload=payload):
                status, body = self.request("POST", payload=payload)
                self.assertEqual(status, 400)
                self.assertFalse(body["ok"])

    def test_wrong_content_type_rejected(self):
        req = Request(self.base + "/v1/services", data=b"{}", headers={
            "Authorization": f"Bearer {TOKEN}", "Content-Type": "text/plain"
        }, method="POST")
        with self.assertRaises(HTTPError) as caught:
            urlopen(req, timeout=2)
        self.assertEqual(caught.exception.code, 400)

    def test_server_refuses_non_loopback(self):
        with self.assertRaisesRegex(ValueError, "gateway_must_bind_to_loopback"):
            LoopbackGatewayServer(("0.0.0.0", 0), ServiceRegistry(), TOKEN)

    def test_bad_token_rejected(self):
        status, body = self.request(token="incorrect-token-value-that-is-long")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "unauthorized")


if __name__ == "__main__":
    unittest.main()
