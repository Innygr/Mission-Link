# MissionLink

Custom encrypted LoRa messaging for XIAO ESP32-S3 + Wio-SX1262.

## Current scaffold

- USB serial command interface
- BLE GATT command interface (ESP32-S3)
- Direct node addressing and group/channel addressing in the packet model
- Versioned packet codec with bounded fields
- Relay-ready packet metadata (hop limit, hop count, message ID)
- PlatformIO host-independent protocol tests

**Important:** This is the software scaffold, not yet a validated radio firmware build. The exact Wio-SX1262 pin mapping, RF switch setup, and regional radio configuration must be confirmed for your hardware revision before enabling RF transmission. Do not transmit until those settings are verified for Canadian compliance.

## Build

Install PlatformIO Core, then from this directory:

```sh
pio run
pio test -e native
```

The `esp32-s3-devkitc-1` target is a starting compile target only; it is not a guarantee that the XIAO/Wio board wiring is configured correctly.

## Serial commands (planned MVP)

- `help`
- `status`
- `nodes`
- `send <node-id> <text>`
- `group <channel-id> <text>`
- `join <channel-id>`
- `leave <channel-id>`

Commands are parsed through one common dispatcher so USB serial and BLE share behavior.

## Encryption and identity status

The packet envelope reserves the fields needed for encrypted payloads, but production encryption/key provisioning is not enabled in this initial scaffold. Before M1 RF tests, implement AES-256-GCM using ESP-IDF's mbedTLS, a persistent per-device identity, unique nonces that cannot repeat under a key, authenticated headers, replay protection, and a documented key-provisioning procedure. Never ship a shared production key in source control.

## Network model

- **Direct node connection:** unicast to one node ID.
- **Group channel:** group ID in the packet; group members decrypt with that group's key.
- **Relay:** relays forward ciphertext based on routing metadata, without group keys.
- **Private direct message:** should use a per-peer/session key, not the group key.
