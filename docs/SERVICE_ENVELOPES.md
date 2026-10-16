# MissionLink service envelopes (v1)

`host/missionlink_envelopes.py` defines a small, versioned JSON envelope for a service request, response, or error. It is a protocol codec and validation layer only; it does not open sockets, authenticate a peer, route packets, or deliver data over LoRa.

## Fields and bounds

The wire format uses compact keys to preserve room for payload data:
- `v`: schema version (`1`).
- `k`: `request`, `response`, or `error`.
- `rid`: bounded correlation ID; responses must copy the request ID.
- `sid` and `op`: service ID and operation, both validated.
- `t` and `x`: creation and expiry timestamps in Unix milliseconds, with a maximum five-minute lifetime.
- `p`: JSON object only, bounded nesting, no NaN/Infinity.
- `e`: error code, required for errors and restricted to a small allowlist.
- The entire UTF-8 wire envelope is capped at 180 bytes. The real radio's usable application payload may be smaller after packet headers and security overhead, so callers must also apply the target transport's own limit.

## Security and future integration

Expiry is a freshness hint, not replay protection. A future gateway must authenticate the sender, authorize each operation, enforce expiry at receive time, deduplicate request IDs, cap request rates, and apply a transport-specific size limit before dispatch. Do not treat a syntactically valid envelope as trusted. Do not send secrets until reviewed end-to-end authenticated encryption and key management exist. Keep `ML_RF_ENABLED=0` until hardware and regulatory gates are explicitly cleared.

Run tests from the repository root:

```sh
python -m unittest discover -s host/tests -v
```
