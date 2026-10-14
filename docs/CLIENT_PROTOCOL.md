# MissionLink client control protocol

Version 1 of the local USB serial/BLE command interface uses UTF-8 commands from clients and JSON objects from firmware. Serial output is newline-delimited JSON (JSON Lines). BLE notifications carry one JSON event each. This is a local control protocol, not the encrypted LoRa wire format.

## Commands

Commands are case-sensitive, trimmed UTF-8 strings. Current accepted command forms:

- `help`
- `status`
- `nodes`
- `send <node-id> <text>`
- `group <channel-id> <text>`
- `join <channel-id>`
- `leave <channel-id>`

The final four command families are placeholders and return `type=error` until the radio and security layers are implemented.

## Events

Status response:

```json
{"type":"status","firmware":"0.2.0","protocolVersion":1,"rfEnabled":false,"bleReady":true,"serialReady":true,"radioReady":false}
```

Node discovery response:

```json
{"type":"nodes","items":[],"ready":false,"reason":"discovery_not_implemented"}
```

Error response:

```json
{"type":"error","code":"not_ready","message":"Direct messaging is unavailable until radio and encryption are implemented."}
```

Boot and BLE events report firmware startup/advertising. Clients should tolerate unknown event types and optional fields for forward compatibility.

## Security boundaries

- USB serial/BLE control commands are not the over-the-air encryption protocol.
- Do not send secrets over BLE until an authenticated pairing/provisioning flow is implemented.
- The LoRa transmitter remains disabled. Never treat the current scaffold as a production secure messenger.
- Future radio payloads must use authenticated encryption and replay protection; routing relays should not need message plaintext keys.
