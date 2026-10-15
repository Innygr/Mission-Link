# Host service dispatch policy

`host/missionlink_dispatch.py` is a transport-independent request dispatcher for the future MissionLink gateway. It validates a service envelope, checks a configured per-principal service allowlist, checks service health and request size, requires an explicitly registered service/operation handler, rejects expired or implausibly future-dated requests, and reserves request IDs in a bounded replay cache before invoking a handler.

## Security boundary

- The `principal_id` argument **must** be supplied by a trusted adapter after successful peer authentication. This module does not authenticate users or devices and must not be exposed directly to an untrusted network.
- The ACL is an allowlist of service IDs per principal. It is not a cryptographic identity system, key store, or permission-management UI.
- Replay suppression is in-memory and process-local. It is not persistent across restarts or distributed between gateways.
- No sockets, HTTP server, LAN discovery, encryption, packet routing, or RF send path is implemented.
- Handlers should be small, bounded, and explicit. Bulk NAS files, AI model data, and general web traffic should use a separately authenticated higher-throughput transport, not be packed into LoRa messages.
- Keep RF disabled until the radio hardware, board mapping, and compliance gates are verified.

## Minimal example

Create a `ServiceRegistry`, register a validated `ServiceRecord`, construct `ServiceDispatcher` with an ACL mapping a verified principal to allowed service IDs, and register each supported `(service_id, operation)` handler explicitly. Call `dispatch(raw_envelope, principal_id=verified_id, now_ms=clock_ms)` only after the transport adapter has authenticated the caller. It returns a correlated response envelope or raises `DispatchError` with a stable rejection code.

Run the host suite from the repository root:

```sh
python -m unittest discover -s host/tests -v
```
