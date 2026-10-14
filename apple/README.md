# MissionLink for Apple

Native SwiftUI + Core Bluetooth starter targeting **iOS 18.0 and later**.

## Build the Xcode project

On a Mac with Xcode installed, install XcodeGen, then from the repository root run:

```sh
brew install xcodegen
cd apple
xcodegen generate
open MissionLink.xcodeproj
```

Select an iOS 18+ simulator or a physical iPhone/iPad. BLE discovery requires a physical device for meaningful testing. Review the generated target's Bluetooth usage-description setting before running.

## Firmware compatibility

The app uses the service/RX/TX UUIDs currently declared in `src/main.cpp`. It scans for that service, subscribes to TX notifications, and writes UTF-8 commands to RX.

## Current limitations

- Starter interface only; not yet a production chat app.
- Firmware commands for nodes, groups, and sending messages are placeholders.
- Radio transmission is deliberately disabled in firmware.
- Key setup, authenticated messaging, reconnection policy, persistence, and end-to-end encrypted chat UI remain to be implemented.
- No Xcode build or device test has been run in this repository environment.
