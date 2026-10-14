# MissionLink testing guide

This guide is for the current **bench-test scaffold**, not a working LoRa messenger. It validates builds, packet/routing policy, USB serial commands, BLE command transport, and the web/native client connection path. It does not validate radio transmission, encryption, range, or real mesh delivery.

## 0. Test safety and prerequisites

- [ ] Use the exact XIAO ESP32-S3 + Wio-SX1262 hardware revision you own; record the labels/revisions before wiring.
- [ ] Keep the antenna connected if the board's radio could ever be enabled; for the current build RF is compile-time disabled.
- [ ] Do not change `ML_RF_ENABLED` from `0`.
- [ ] Do not try to infer radio pins from a different SX1262 board.
- [ ] Install Git, Python 3, and PlatformIO Core. For USB serial testing, use a desktop computer and a known-good USB data cable.
- [ ] Record the tested commit SHA, board revision, OS, and tool versions with the results.

## 1. Get the current code

```sh
git clone https://github.com/Innygr/Mission-Link.git
cd Mission-Link
git switch main
git pull
```

## 2. Run the host-side tests

```sh
pio test -e native
```

**Pass condition:** PlatformIO exits with code 0 and all Unity tests pass. These tests exercise the packet codec and RF-independent mesh routing policy only.

If this fails, save the full terminal output and report the first failing test. Do not proceed as if the test passed.

## 3. Compile the firmware scaffold

```sh
pio run -e xiao_esp32s3
```

**Pass condition:** PlatformIO reports a successful build. The environment currently uses `esp32-s3-devkitc-1` as a compile target; a successful compile is not proof of the exact XIAO/Wio pin mapping.

## 4. Flash and test USB serial

Only flash after reviewing the build target and ensuring the connected board is the intended test board.

```sh
pio run -e xiao_esp32s3 -t upload
pio device monitor -b 115200
```

After boot, expect JSON Lines boot/hint/BLE-advertising events. Send each command followed by Enter:

| Input | Expected result |
|---|---|
| `help` | Help event listing supported commands, presets, and placeholders |
| `status` | Status event; `rfEnabled:false`, `radioReady:false`, preset initially `client` |
| `presets` | Three presets: client, repeater, gateway |
| `preset repeater` | Preset event with `active:repeater` |
| `status` | Status event reports `preset:repeater` |
| `preset gateway` | Preset event with `active:gateway` |
| `preset client` | Preset event with `active:client` |
| `preset not-a-preset` | `invalid_preset` error; active preset should remain unchanged |
| `nodes` | Empty list with `ready:false` and `discovery_not_implemented` |
| `send demo hello` | `not_ready` error; no message is transmitted |
| `group demo hello` | `not_ready` error; no message is transmitted |

Also check:
- [ ] Status continues to report `rfEnabled:false` and `radioReady:false` for every preset.
- [ ] Reboot resets the preset to Client (selection is intentionally volatile).
- [ ] A USB line longer than 256 bytes is discarded whole and reports `command_too_long`; its truncated prefix must not run as a command.
- [ ] Save the complete boot log and command/response transcript.

## 5. Test BLE transport

Use the native MissionLink Apple app or a BLE GATT client that can write to and subscribe to the characteristics below. Keep BLE testing limited to non-secret diagnostic commands.

- Device name: `MissionLink`
- Service UUID: `3f4a0001-7c2e-4a5b-9d11-5b7d6e100001`
- RX write UUID: `3f4a0002-7c2e-4a5b-9d11-5b7d6e100001`
- TX read/notify UUID: `3f4a0003-7c2e-4a5b-9d11-5b7d6e100001`

- [ ] Scan and connect to the device.
- [ ] Subscribe to TX notifications and read the TX value.
- [ ] Write `status`, then verify a JSON status event is received.
- [ ] Write `presets` and `preset repeater`; verify the expected events.
- [ ] Disconnect/reconnect and confirm the firmware still advertises.
- [ ] Check that oversized BLE writes are rejected.
- [ ] Do not treat a successful BLE write as proof that a response was delivered; notifications are best-effort.

The BLE interface and physical-device app behavior have not been confirmed by this guide; mark each result as pass/fail/not tested.

## 6. Run the web flasher only when needed

The web flasher requires a supported desktop Chromium browser over HTTPS and Web Serial. It does not work with USB serial from iOS Safari. Use only firmware built for the exact board and flash layout. Do not select an arbitrary binary or enable RF through a web UI.

## 7. Explicitly out of scope for this test stage

Do **not** mark these as working yet:

- LoRa radio initialization, receive, or transmit
- Encrypted messaging or key provisioning
- Actual over-the-air Client/Repeater/Gateway behavior
- Node discovery, group membership, acknowledgements, retries, or store-and-forward
- Range, reliability, battery life, or regulatory compliance claims

Radio testing requires verified hardware pin mapping and Canadian radio settings, plus an implemented authentication/encryption and replay-protection layer before user messages are sent over RF.

## 8. Results template

Copy this block into a test report:

```text
Commit SHA:
Date/time (local):
Tester:
Host OS:
Python / PlatformIO versions:
Board revision:
USB cable/port:
Native tests: PASS / FAIL / NOT RUN
ESP32 build: PASS / FAIL / NOT RUN
Upload/boot: PASS / FAIL / NOT RUN
Serial command matrix: PASS / FAIL / PARTIAL / NOT RUN
Oversized serial input: PASS / FAIL / NOT RUN
BLE scan/connect: PASS / FAIL / NOT RUN
BLE command/notify: PASS / FAIL / NOT RUN
Oversized BLE write: PASS / FAIL / NOT RUN
RF confirmed disabled: YES / NO
Logs or first failure:
Notes:
```

Do not report a test as passed unless it was actually run and the result was observed.
