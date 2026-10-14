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

## Testing the firmware flasher (`flasher.html`)

Not yet verified on real hardware. The page loads this repository's CI firmware build from `web/firmware/` by default; picking a file overrides that slot. To try it on a spare XIAO ESP32-S3:

1. Open the deployed `flasher.html` in desktop Chrome or Edge. For local testing, run `pio run -e xiao_esp32s3`, stage `web/firmware/` as `.github/workflows/deploy-web.yml` does, and serve `web/` over localhost (see above).
2. Connect (hold BOOT while plugging in if needed), then flash.
3. Press RESET and check serial output at 115200 baud.

Before writing, the page checks image headers, the ESP32-S3 chip ID, slot sizes and the app partition. After each file is written, esptool-js compares an MD5 read back from flash. Host tests: `node --test web/tests/flasher-validate.test.mjs`. Emulator end-to-end test and its limits: `web/tests/e2e/README.md`.
