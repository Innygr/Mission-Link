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

Not yet verified on hardware. To try it on a spare XIAO ESP32-S3:

1. Build: `pio run -e xiao_esp32s3`.
2. Serve `web/` over localhost (see above) and open `flasher.html` in desktop Chrome or Edge.
3. Select these files:
   - Bootloader (0x0): `.pio/build/xiao_esp32s3/bootloader.bin`
   - Partition table (0x8000): `.pio/build/xiao_esp32s3/partitions.bin`
   - Boot app (0xE000): `~/.platformio/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin`
   - Application (0x10000): `.pio/build/xiao_esp32s3/firmware.bin`
4. Connect (hold BOOT while plugging in if needed), flash, then press RESET and check serial output at 115200 baud.

Before writing, the page checks image headers, the ESP32-S3 chip ID, slot sizes and the app partition. After each file is written, esptool-js compares an MD5 read back from flash. Host-side tests for these checks: `node --test web/tests/flasher-validate.test.mjs`.
