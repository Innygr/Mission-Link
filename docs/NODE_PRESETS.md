# MissionLink node presets

| Preset | Behavior |
|---|---|
| Client | End device. Accepts direct messages addressed to itself and local group/broadcast traffic; never relays packets. |
| Repeater | Relay-only for transit traffic. Forwards unknown direct destinations and group/broadcast frames within hop/rate limits. Does not surface group/broadcast payloads to the local app. |
| Gateway | Relays traffic and also delivers group/broadcast payloads locally. Intended to bridge the mesh to a local client/control interface; that bridge is not implemented yet. |

Firmware commands (USB serial and BLE command interface):
- `presets` lists available presets.
- `preset client`
- `preset repeater`
- `preset gateway`
- `status` reports the active preset.

Selection is currently RAM-only; reboot returns to Client. The routing policy is not connected to the radio receive/transmit path, so these presets do not yet enable over-the-air relaying. RF remains disabled until exact hardware, security, and Canadian regional settings are verified.
