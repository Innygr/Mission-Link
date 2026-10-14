# Mesh router simulator — implementation status

The portable MeshRouter is a routing-policy simulator module, not a radio driver. It can be unit-tested without hardware and deliberately has no RF calls.

## Current behavior
- Validates protocol version, packet type/address mode, payload bound, hop budget, nonzero source/message IDs, and rejects a packet claiming to originate at the receiving node.
- Uses a fixed 64-entry duplicate cache keyed by source ID + message ID, with 60-second expiry.
- Forwards unknown direct-unicast destinations as bounded flood traffic; delivers locally when destination matches.
- Delivers group/broadcast packets locally and forwards them while hop budget remains.
- Increments hop count exactly once for a forward decision.
- Limits a node to 8 forwards per one-second window globally and 3 per source in that window.
- Uses fixed-size storage for duplicate/rate-limit state.

## Important limitations before device testing
This is not end-to-end mesh messaging yet. There is no LoRa send/receive integration, radio configuration, node discovery, acknowledgement/retry, authenticated encryption, replay authentication, or real stable-ID provisioning. Rate limits are local safety rails, not a complete airtime scheduler. Do not enable RF or send private data with this module. Radio integration remains gated on exact board/pin verification, security, and Canadian regional compliance review.

## Native tests
Run pio test -e native. Tests cover a simulated A → B → C path, duplicate suppression, hop limit, cache expiry, invalid identity fields, and global forwarding limits, alongside packet codec tests.
