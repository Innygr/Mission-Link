# MissionLink cipher suites and glyph transport

## Goals

MissionLink separates cryptographic protection from how encrypted bytes are represented. A cipher suite is security-sensitive; a glyph view is only a presentation/obfuscation feature.

## Cipher suite registry (proposed; not implemented yet)

| ID | Name | Intended use | Status |
|---|---|---|---|
| 0x01 | AES-256-GCM | Default production suite | Planned |
| 0x02 | ChaCha20-Poly1305 | Alternative authenticated-encryption suite | Planned |
| 0x80 | Classical-cipher demo | Educational Caesar/Vigenere demonstrations only | Optional future demo; never for private traffic |

Production suites must provide authenticated encryption. Do not implement a home-grown cipher, silently downgrade between suites, or accept unauthenticated plaintext as a fallback. Peers must negotiate or be configured for an allowed suite and reject unsupported suite IDs.

### Required security rules

- Use a vetted implementation from the platform crypto library (ESP-IDF mbedTLS where supported).
- Never reuse a nonce with the same key. Define and test a per-key nonce allocation strategy before sending any encrypted radio packet.
- Authenticate immutable packet metadata as associated data, including protocol version, suite ID, source/destination, message ID, and channel/address mode. Mutable relay fields such as hop count need a separate design so legitimate forwarding does not invalidate authentication.
- Verify authentication before exposing plaintext. Reject duplicate/replayed message IDs within a defined replay window.
- Keep private-message keys separate from group keys. Relays forward ciphertext and do not receive message keys.
- Define key provisioning, rotation, revocation, and device-reset behavior before calling the system production-secure.
- Do not put keys or plaintext secrets in logs, test fixtures, or source control.

## Wingdings-style transport mode

### Important distinction

LoRa carries bytes, not font glyphs. Wingdings is a font mapping, not an encryption algorithm or a portable wire encoding. Simply changing the font does not change the bytes sent over radio and does not protect a message.

### Proposed behavior

1. Encode the message in UTF-8.
2. Encrypt it with the selected authenticated-encryption suite.
3. Optionally apply a **glyph transport representation** to the ciphertext for the requested Wingdings-style mode.
4. The receiver reverses the representation, verifies/decrypts the ciphertext, then decodes UTF-8.

The wire protocol should use a documented, stable symbol-ID alphabet rather than depending on the recipient having a particular Wingdings font installed. Clients can render those symbol IDs using a Wingdings-inspired glyph set. A text/debug export may render a Wingdings-like string, while the actual LoRa frame still carries a compact byte representation.

The glyph mode is a disguise/visual effect only. Security comes entirely from the authenticated-encryption layer. It must never be applied to keys, nonce generation, or authentication tags as a substitute for cryptography.

### Efficiency and interoperability

A literal text representation of encrypted data can substantially increase packet size and fragment messages. The default radio mode should therefore remain compact binary ciphertext. If glyph mode is enabled for actual radio payloads, it must have an explicit encoding ID, strict size limits, round-trip tests, and fragmentation/reassembly rules. Unknown encoding IDs must be rejected, not guessed.

## Implementation gates

Do not enable RF until all of the following exist and are tested:

- Authenticated-encryption implementation and test vectors for every production suite.
- Nonce uniqueness and replay protection tests.
- A reviewed packet-header/AAD design that supports relays.
- Key provisioning and group/direct key lifecycle.
- Glyph encoding/decoding round-trip tests and packet-size measurements.
- Verified pin mapping, radio configuration, and applicable Canadian radio compliance.
