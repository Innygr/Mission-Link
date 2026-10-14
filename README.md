# MissionLink

Custom encrypted LoRa messaging for XIAO ESP32-S3 + Wio-SX1262.

## Project status

This is an actively developing scaffold, **not yet a validated radio firmware build or production messaging system**. RF transmission is deliberately disabled. The exact Wio-SX1262 pin mapping, RF switch setup, and regional radio configuration must be confirmed for the exact hardware revision before enabling RF transmission. Verify Canadian compliance before transmitting.

## Client applications

- **Web/PWA:** `web/` — responsive local dashboard, installable web app manifest, offline static-asset caching, and a USB serial console in supported desktop Chromium browsers.
- **Apple app:** `apple/MissionLink/` — SwiftUI + Core Bluetooth starter targeting iOS 18 and later. It uses the GATT UUIDs currently in `src/main.cpp`.
- **Architecture notes:** `docs/CLIENT_ARCHITECTURE.md`.
- **Shared command/event schema:** `docs/CLIENT_PROTOCOL.md`.

Safari on iOS does not support Web Bluetooth, so the PWA cannot directly connect to the radio over BLE. Use the native Apple app for direct BLE access. The iOS app source is a starter and must be opened in Xcode, built, and tested on a physical device; no build/device validation has been performed yet.

A GitHub Actions workflow is included to deploy `web/` to GitHub Pages. In the repository settings, set Pages' build/deployment source to **GitHub Actions** before expecting a published site.

## Firmware scaffold (0.2.0)

- USB serial command interface
- BLE GATT command interface (ESP32-S3)
- Direct node addressing and group/channel addressing in the packet model
- Versioned packet codec with bounded fields
- Relay-ready packet metadata (hop limit, hop count, message ID)
- PlatformIO host-independent protocol tests

## Build

Install PlatformIO Core, then from the repository root:

```sh
pio run
pio test -e native
```

The `esp32-s3-devkitc-1` target is a starting compile target only; it does not guarantee that the XIAO/Wio board wiring is configured correctly. The build and tests have not yet been run in this development session.

## Serial/BLE commands (planned MVP)

- `help`
- `status`
- `nodes`
- `send <node-id> <text>`
- `group <channel-id> <text>`
- `join <channel-id>`
- `leave <channel-id>`

Commands are parsed through one common dispatcher so USB serial and BLE share behavior. Node discovery, group membership, and message delivery remain placeholders.

## Encryption and identity status

Production encryption/key provisioning is not implemented yet. Before M1 RF tests, implement AES-256-GCM using ESP-IDF's mbedTLS, persistent per-device identity, nonces that cannot repeat under a key, authenticated headers, replay protection, and documented key provisioning. Never commit a shared production key to source control.

## Network model

- **Direct node connection:** unicast to one node ID.
- **Group channel:** group ID in the packet; group members decrypt with that group's key.
- **Relay:** relays forward ciphertext based on routing metadata, without group keys.
- **Private direct message:** use a per-peer/session key, not the group key.
