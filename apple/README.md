# MissionLink for Apple

Native SwiftUI + Core Bluetooth starter targeting **iOS 18.0 and later**.

## Open in Xcode

1. On a Mac with Xcode installed, create an iOS App project named `MissionLink` using SwiftUI.
2. Set the deployment target to iOS 18.0.
3. Replace the generated app entry point and view with the Swift files in `apple/MissionLink/`.
4. Add `Info.plist` Bluetooth usage text to the app target's generated Info.plist (or configure the target to use this plist).
5. Run on a physical iPhone/iPad with Bluetooth enabled. BLE device discovery is not reliably testable in the simulator.

## Firmware compatibility

The app uses the service/RX/TX UUIDs currently declared in `src/main.cpp`. It scans for that service, subscribes to TX notifications, and writes UTF-8 commands to RX.

## Current limitations

- Starter interface only; not yet a production chat app.
- Firmware commands for nodes, groups, and sending messages are placeholders.
- Radio transmission is deliberately disabled in firmware.
- Key setup, authenticated messaging, reconnection policy, persistence, and end-to-end encrypted chat UI remain to be implemented.
- No Xcode build or device test has been run in this repository environment.
