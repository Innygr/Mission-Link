# MissionLink packet format (protocol v1)

This document describes the current binary packet codec implemented in `include/missionlink_packet.h` and `src/packet_codec.cpp`. It is a wire-format draft, not a guarantee that packets are currently transmitted over LoRa.

## Frame layout

All multibyte integers are big-endian. The fixed header is 32 bytes; the payload follows immediately.

| Byte offset | Length | Field | Meaning |
|---:|---:|---|---|
| 0 | 1 | Version | Must equal protocol version `1` |
| 1 | 1 | Packet type | `1` Hello, `2` Data, `3` Ack, `4` Status, `5` Join, `6` Leave |
| 2 | 1 | Address mode | `0` Direct, `1` Group, `2` Broadcast |
| 3 | 1 | Flags | Reserved for protocol-defined flags |
| 4–11 | 8 | Source ID | Sender node identifier |
| 12–19 | 8 | Destination ID | Destination node or group/broadcast identifier according to address mode |
| 20–27 | 8 | Message ID | Message identifier for deduplication/acknowledgement design |
| 28 | 1 | Hop limit | Maximum permitted hop count; current codec permits at most 4 |
| 29 | 1 | Hop count | Number of hops already traversed; must not exceed hop limit |
| 30–31 | 2 | Payload length | Unsigned payload length in bytes, big-endian |
| 32 onward | Variable | Payload | 0–180 opaque bytes |

The current maximum encoded frame size is **212 bytes** (32-byte header + 180-byte payload). This may be larger than a practical radio packet once a future encryption tag, nonce, and radio-specific overhead are accounted for. The final over-the-air size budget must be defined before radio transport is implemented.

## Validation performed by the codec

- Rejects null or truncated input.
- Rejects unknown protocol versions, packet types, and address modes.
- Rejects hop limits above the configured maximum or hop counts above the hop limit.
- Rejects payload lengths above 180 bytes and any frame whose actual length differs from the declared length.
- Rejects unsupported values on encode and clears the output buffer if encoding fails.

## Important security boundary

The codec is **not encryption**. It serializes and validates fields only. The payload must be passed through a reviewed authenticated-encryption layer before any future radio transmission. A future protocol revision must define authenticated headers, nonce construction, replay protection, message-ID uniqueness, and the impact of authentication tags on the maximum frame size. Relays must not need message plaintext keys.

The current firmware keeps RF disabled. Do not treat this format draft as a production messaging protocol.
