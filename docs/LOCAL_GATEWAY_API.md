# Local MissionLink Gateway API (experimental)

This module adds a small HTTP boundary for clients running on the same computer as a MissionLink host service. It is deliberately **loopback-only** and is not a LAN server, Internet endpoint, mesh transport, or radio gateway.

## Current endpoints

- `GET /v1/services` — requires a bearer token; returns healthy service metadata only. It omits endpoint URLs and other private host details.
- `POST /v1/dispatch` — requires a bearer token and `Content-Type: application/json`; body is one compact MissionLink service envelope, limited to 180 bytes. The authenticated token maps to a dispatcher principal, then the existing dispatcher applies its service ACL, expiry, replay, health, operation, and payload checks.

Responses include `Cache-Control: no-store`, a bounded content length, and stable error codes. Authorization headers, request bodies, and request paths are not logged by the handler.

## Minimal embedding example

The gateway is a library component, not a turnkey daemon or installer. A host application must explicitly construct the registry, register service handlers, configure the dispatcher ACL, and provision a high-entropy local token out-of-band.

```python
import secrets

from host.missionlink_dispatch import ServiceDispatcher
from host.missionlink_gateway import create_gateway_server
from host.missionlink_services import ServiceRegistry

registry = ServiceRegistry()
# Register ServiceRecord objects and explicitly registered service handlers.
dispatcher = ServiceDispatcher(registry, {"desktop-client": frozenset()})
token = secrets.token_urlsafe(32)

server = create_gateway_server(
    "127.0.0.1", 8765, dispatcher, registry, {token: "desktop-client"}
)
try:
    server.serve_forever()
finally:
    server.server_close()
```

The example intentionally grants no service access; replace the empty set only with explicitly approved service IDs. Never commit real tokens or send them in logs or issue reports.

## Security boundary and limitations

- The bind host must be a literal loopback IP. Hostnames (including `localhost`) and non-loopback addresses are rejected to avoid DNS ambiguity and accidental LAN exposure.
- Use a random token with at least 32 characters; keep it private. Tokens identify a configured principal but do not provide user accounts, token rotation, device identity, or cryptographic end-to-end identity.
- HTTP is unencrypted. Loopback binding reduces network exposure but is not a substitute for OS account isolation; other local processes may be able to connect if they obtain the token.
- No CORS browser API, TLS, remote listener, pairing flow, persistent replay database, rate-limiting policy, service plugin loader, or process supervisor is included.
- The in-memory replay cache can reset on restart. Do not use this API as a production public-facing service.
- This API does not bridge requests onto LoRa or prove radio delivery. The existing 180-byte envelope ceiling is not a guarantee of available radio payload after future packet/security overhead.
- RF stays disabled by default; no physical hardware or over-the-air test is claimed.

## Tests

Run the repository host suite with:

```sh
python -m unittest discover -s host/tests -v
```
