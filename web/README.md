# MissionLink Web

Static, dependency-free dashboard. No bundler is required.

## Run locally

Because Web Serial requires a secure context, use HTTPS or localhost. For example:

```sh
python3 -m http.server 8000 --directory web
```

Then open `http://localhost:8000` in a supported desktop Chromium browser and connect the device over USB serial. A browser without Web Serial can still display the dashboard, but cannot connect to USB.

## iPhone and iPad

The PWA can be opened in Safari and added to the Home Screen for the dashboard experience. iOS Safari does not expose Web Bluetooth, so direct BLE connection to the radio is implemented in the native SwiftUI app under `apple/MissionLink/`.

## Current limitations

- This is a control-console preview, not yet a chat client.
- Firmware currently returns JSON Lines status/help/error events.
- Node discovery, channels, encryption, and radio sending are not implemented.
- RF transmission is disabled in firmware.
