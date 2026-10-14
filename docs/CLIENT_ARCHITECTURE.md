# MissionLink client architecture

## Client targets

- **Web/PWA:** `web/`. Responsive, installable dashboard with offline static assets. USB serial is available only in browsers that implement Web Serial, normally desktop Chromium over a secure context.
- **Apple app:** `apple/MissionLink/`. SwiftUI + Core Bluetooth, minimum deployment target iOS 18.0. Uses the firmware's GATT UUIDs.
- **Firmware:** USB serial and BLE should feed the same command dispatcher; the web and Apple clients must not invent separate protocol semantics.

## Important iOS browser limitation

Safari on iOS does not implement the Web Bluetooth API. A PWA alone therefore cannot directly scan/connect to the ESP32 BLE peripheral. The native iOS client uses Core Bluetooth for that job. The PWA can still provide documentation, settings, status dashboards, and any future network-backed functionality.

## Command protocol status

Current firmware commands are plain UTF-8 lines over serial/BLE. This is a development control interface, not the encrypted over-the-air packet format. Do not send private or sensitive information over an untrusted BLE connection until pairing/authentication is added. RF stays disabled until board wiring, regional settings, and encryption are reviewed.

## Next client milestones

1. Make firmware responses machine-readable (JSON Lines or a versioned binary envelope).
2. Add explicit BLE pairing/authentication and a documented key setup flow.
3. Implement nodes/channels/message events and ACK states.
4. Add native iOS reconnection and accessibility testing.
5. Test the PWA on desktop and iOS 18 Safari; test BLE on physical iOS hardware.
