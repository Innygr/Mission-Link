# MissionLink 

Custom encrypted LoRa messaging for XIAO ESP32-S3 + Wio-SX1262.

## Project status

This is an actively developing scaffold, **not yet a validated radio firmware build or production messaging system**. RF transmission is deliberately disabled. The exact Wio-SX1262 pin mapping, RF switch setup, and regional radio configuration must be confirmed for the exact hardware revision before enabling RF transmission. Verify Canadian compliance before transmitting.

## Client applications

- **Web/PWA:** `web/` — responsive local dashboard, installable web app manifest, offline static-asset caching, and a USB serial console in supported desktop Chromium browsers.
- **Visual test bench:** [`web/testbench.html`](web/testbench.html) — point-and-click USB diagnostics, preset switching, and a firmware response test suite without needing a terminal.
- **Web flasher:** [`web/flasher.html`](web/flasher.html) — flash CI-built binaries from a supported desktop Chromium browser; download the firmware artifact from [Firmware Builds](https://github.com/Innygr/Mission-Link/actions/workflows/firmware-ci.yml) after a successful build.
- **Apple app:** `apple/MissionLink/` — SwiftUI + Core Bluetooth starter targeting iOS 16.7 and later. It uses the GATT UUIDs currently in `src/main.cpp`.
- **Architecture notes:** `docs/CLIENT_ARCHITECTURE.md`.
- **Security and glyph transport design:** `docs/CIPHER_SUITES.md` (design proposal; not implemented in firmware yet).
- **Shared command/event schema:** `docs/CLIENT_PROTOCOL.md`.
- **Binary packet format:** `docs/PACKET_FORMAT.md` (protocol v1 codec layout and validation rules).
- **Radio bring-up checklist:** `docs/RADIO_BRINGUP.md` (staged hardware validation; RF remains disabled).
- **Bench testing guide:** `docs/TESTING_GUIDE.md` — step-by-step native tests, compile, USB serial, BLE, expected responses, and a test-report template.
- **Radio adapter:** `src/missionlink_radio.cpp` and `include/missionlink_radio.h` (feature-gated SX1262/RadioLib adapter for receive, decode, RSSI/SNR, and encoded-frame transmit; pin map and RF remain disabled until verified).\n- **Mesh routing module:** `src/mesh_router.cpp` and `include/mesh_router.h` (RF-independent routing policy and native simulation tests; guarded receive-to-router integration is present, but RF is disabled and real mesh delivery is unverified).
- **Node presets:** `docs/NODE_PRESETS.md` — Client, Repeater, and Gateway roles.

Safari on iOS does not support Web Bluetooth, so the PWA cannot directly connect to the radio over BLE. Use the native Apple app for direct BLE access. The iOS app source is a starter. An iOS simulator build check is defined in GitHub Actions; physical-device BLE behavior still needs testing.

A GitHub Actions workflow validates and deploys `web/` to GitHub Pages. The latest logo integration deployment succeeded; installed PWAs may need a reload to refresh cached assets.

## Firmware scaffold (0.2.1)

- USB serial command interface
- BLE GATT command interface (ESP32-S3)
- Direct node addressing and group/channel addressing in the packet model
- Versioned packet codec with bounded fields
- Relay-ready packet metadata (hop limit, hop count, message ID)
- Feature-gated SX1262 radio adapter interface with receive/decode path and a compile-time RF transmit guard (hardware pin map unverified; disabled by default)\n- RF-independent mesh forwarding policy with duplicate suppression, bounded hop counts, and forwarding rate limits (simulator only)
- Client / Repeater / Gateway routing presets (volatile selection; radio integration pending)
- PlatformIO host-independent protocol tests, including malformed-frame rejection
- JSON Lines status/help/error events shared by USB serial and BLE
- Bounded command input: oversized USB lines are discarded whole, and oversized BLE writes are rejected
- GitHub Actions workflows for web validation, packet tests, ESP32 compile, and iOS simulator compile

## Build

Install PlatformIO Core, then from the repository root:

```sh
pio test -e native
pio run -e xiao_esp32s3
```

The `esp32-s3-devkitc-1` target is a starting compile target only; it does not guarantee that the XIAO/Wio board wiring is configured correctly. CI runs native packet-codec and mesh-policy tests and compiles the ESP32-S3 scaffold; the exact hardware configuration and RF operation still require bench testing.

## Serial/BLE commands

- `help`
- `status`
- `nodes`
- `presets`
- `preset client`
- `preset repeater`
- `preset gateway`
- `send <node-id> <text>` (placeholder; returns `not_ready`)
- `group <channel-id> <text>` (placeholder; returns `not_ready`)
- `join <channel-id>` (placeholder; returns `not_ready`)
- `leave <channel-id>` (placeholder; returns `not_ready`)

Commands are parsed through one common dispatcher so USB serial and BLE share behavior. Responses use JSON Lines on serial and one JSON event per BLE notification. Node discovery, group membership, and message delivery remain placeholders; see `docs/CLIENT_PROTOCOL.md`. Preset selection is volatile and resets to Client on reboot. Presets do not turn on the radio or cause real over-the-air relaying.

## Encryption and identity status

Production encryption/key provisioning is not implemented yet. The planned cipher suites and optional Wingdings-style ciphertext representation are documented in `docs/CIPHER_SUITES.md`. Before RF tests, implement authenticated encryption, persistent per-device identity, nonces that cannot repeat under a key, authenticated headers, replay protection, and documented key provisioning. Never commit a shared production key to source control.

## Network model

- **Implementation order:** mesh routing first, then direct P2P optimisation. See [mesh-first routing plan](docs/MESH_FIRST_ROUTING.md), [mesh routing test plan](docs/MESH_ROUTING_TEST_PLAN.md), and [mesh simulator implementation notes](docs/MESH_ROUTER_SIMULATOR.md).
- **Direct node connection:** unicast to one node ID.
- **Group channel:** group ID in the packet; group members decrypt with that group's key.
- **Relay:** relays forward ciphertext based on routing metadata, without group keys.


## Contributing and AI collaboration

This repository uses a shared handoff protocol for human and AI-assisted contributors:

- [Contributor instructions](AGENTS.md)
- [AI collaboration workflow](docs/AI_COLLABORATION.md)
- [Current AI work status and handoff log](docs/AI_STATUS.md)
- [AI task / handoff issue template](.github/ISSUE_TEMPLATE/ai-task.yml)
- [Coordination issue #1](https://github.com/Innygr/Mission-Link/issues/1)

The repository and its issue tracker provide a shared record, not an automatic live bridge between ChatGPT and Claude. Confirm that each assistant's current integration can access the relevant files or issue before relying on a handoff. RF remains disabled until the hardware configuration and regional requirements are verified.
