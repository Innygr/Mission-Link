# MissionLink

Custom encrypted LoRa messaging for XIAO ESP32-S3 + Wio-SX1262.

## Initial scaffold

- USB serial command interface
- BLE GATT command interface (ESP32-S3)
- Direct-node and group/channel addressing in the packet model
- Relay-ready packet metadata (message ID, hop limit, hop count)
- PlatformIO project and host-side packet codec tests

**This is an initial scaffold, not validated radio firmware.** Verify the exact Wio-SX1262 revision, board pin mapping, RF switch setup, and Canadian-compliant radio configuration before enabling RF transmission.

## Build

Install PlatformIO Core:

```sh
pio run
pio test -e native
```

The ESP32-S3 target is a generic compile starting point; it does not guarantee the XIAO/Wio wiring is correct.

## Initial commands

- `help`
- `status`
- `nodes`
- `send <node-id> <text>`
- `group <channel-id> <text>`
- `join <channel-id>`
- `leave <channel-id>`

USB serial and BLE share one command dispatcher.

## Security status

Production encryption and key provisioning are **not yet implemented**. Before RF tests, implement AES-256-GCM using a vetted library, nonce uniqueness across resets, authenticated routing metadata, replay protection, and secure key provisioning. Never commit production keys. Fail closed: do not send plaintext if encryption fails.

## Network model

- Direct message: unicast to one node ID.
- Group channel: group ID with a channel-specific key.
- Relay: forwards ciphertext using routing metadata without message keys.
- Private direct messages: use a per-peer/session key, not the group key.

## Roadmap

1. Verify hardware revision and build baseline.
2. Implement authenticated encryption and replay protection.
3. Integrate SX1262 driver and compliant regional settings.
4. Implement direct messaging and end-to-end acknowledgements.
5. Add relay queues, duplicate suppression, and group channels.
6. Test four nodes; record delivery rate, RSSI, and SNR.
