# Mesh-first routing plan

MissionLink is **mesh-first**. Direct peer-to-peer delivery will be added after the multi-hop mesh foundation is implemented and tested.

## Scope and honest status

This document defines the implementation order; it is not a claim that mesh routing already works. The current firmware has a validated packet codec and relay metadata, but no active LoRa send/receive path, routing table, relay forwarding, encryption, acknowledgements, or retransmission. RF remains disabled (ML_RF_ENABLED = 0).

## Phase 1 — safe mesh foundation

1. **Stable identity and packet validation**
   - Give every node a stable 64-bit ID.
   - Validate packet type, destination mode, hop limit/count, payload bounds, and message ID before routing.
   - Do not treat a sender-provided source ID as authenticated until the security layer verifies it.
2. **Flood-based discovery, then bounded forwarding**
   - Begin with controlled, rate-limited flooding rather than pretending a route table exists.
   - Cache message IDs with an expiry to suppress duplicates.
   - Increment hop count exactly once per forward; never forward when the budget is exhausted.
   - Apply per-source and global forwarding limits so broadcast storms cannot consume all airtime.
3. **Store-and-forward**
   - Queue messages briefly when a next hop is unavailable, with fixed memory limits and expiry.
   - Never persist plaintext message content before encryption is implemented.
4. **Reliability**
   - Add acknowledgements, retry limits, randomized backoff, and duplicate suppression.
   - Distinguish accepted by local radio, relayed, and delivered to destination in client events.
5. **Authenticated encryption before enabling RF**
   - Encrypt message payloads end-to-end and authenticate immutable routing-relevant fields.
   - Relays should forward ciphertext and must not need recipients' message keys.
   - Add replay protection and key provisioning/rotation before real user traffic.
6. **Hardware and compliance gate**
   - Confirm the exact XIAO + Wio-SX1262 revision, pins, RF switch, antenna, and legal regional radio parameters.
   - Bench-test receive-only first, then a controlled low-risk test.
   - Keep ML_RF_ENABLED = 0 until this gate is explicitly completed.

## Phase 2 — direct P2P optimisation

Once mesh forwarding is reliable, add direct unicast as the preferred one-hop route when a destination is reachable. If it fails, the message should fall back to mesh routing without requiring the user to choose a different mode. Private direct messages use per-peer/session keys; group messages use separate group keys.

## Client behaviour

The app should present one Send action. The network layer chooses the route:
- one hop available → direct delivery;
- destination not directly reachable → mesh forwarding;
- no route/acknowledgement → bounded retry and a clear pending/failed state.

The UI must not claim delivery from a successful local command write or radio enqueue alone.

## Test gates

- Packet codec fuzz/malformed-input tests.
- Duplicate and hop-budget tests.
- Loop/storm prevention and bounded queue tests.
- Simulated A → B → C forwarding and unreachable destination cases.
- Authentication/replay tests before RF transmission is enabled.
- Physical multi-node tests only after hardware and compliance review.
