# SX1262 adapter integration

The first RadioLib adapter lives in `include/missionlink_radio.h` and `src/missionlink_radio.cpp`.

## What is implemented

- A single firmware-facing radio interface for initialization, polling received frames, packet decoding, RSSI/SNR capture, and encoded-frame transmission.
- Radio initialization is compile-time gated by `ML_RADIO_PINMAP_VERIFIED` and `ML_RADIO_RX_ENABLED`.
- The transmit method refuses to transmit unless `ML_RF_ENABLED` is enabled.
- Pin, modem, and regional parameters are deliberately required from a verified board-specific configuration. The adapter does not invent pin numbers or regional RF settings.
- Invalid/oversized received frames are rejected before decoding.

## Still required before hardware operation

1. Verify the exact XIAO ESP32-S3 and Wio-SX1262 board revisions and their official wiring.
2. Add a board-specific configuration with the verified SPI, CS, DIO1, reset, busy, and compliant regional modem settings.
3. Check the RadioLib version/API against the selected dependency and compile with the verified pin-map feature enabled.
4. The firmware loop now polls received frames, passes them through the mesh router, attempts guarded forwarding, and reports mesh events over serial/BLE.
5. Implement authenticated encryption, replay protection, node identity, acknowledgements, retry policy, and key provisioning before sending user messages.
6. Run receive-only tests with a known compatible authorized transmitter before any controlled transmit test.

**Current default remains safe/inert:** `ML_RF_ENABLED=0`, `ML_RADIO_PINMAP_VERIFIED=0`, and `ML_RADIO_RX_ENABLED=0`. This is an integration step, not a claim that radio hardware has been validated or that end-to-end messaging is ready.
