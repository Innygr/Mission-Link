# Optional status screen

If an **SSD1306** I2C OLED is attached, the firmware shows live connectivity on it. Without one, nothing changes.

## Supported screens

| Screen | Build flag | Layout |
|---|---|---|
| XIAO ML Kit 0.42" **72×40** (`U8G2_SSD1306_72X40_ER`, rotated 180°, as in the maker100 `xiaoML-kit` sketches) | default | 5 rows × 14 chars, 5×7 font |
| XIAO expansion board 0.96" **128×64** (`U8G2_SSD1306_128X64_NONAME`) | `-D ML_DISPLAY_128X64=1` | 6 rows × 21 chars, 6×10 font |

Both screens answer at the same I2C address and the SSD1306 has no ID register, so the size can't be detected at runtime and is chosen at build time. SH1106-based 1.3" screens aren't supported.

## Detection

- At boot, and every 5 s while no screen is found, the firmware probes I2C addresses `0x3C` and `0x3D` on the board's default pins: XIAO ESP32-S3 `SDA = GPIO5 (D4)`, `SCL = GPIO6 (D5)`. These are the same pins Meshtastic's `seeed_xiao_s3` variant uses for its screen, and they don't overlap the Wio-SX1262 pins.
- If an address acknowledges, the screen is initialised. It is redrawn at most every 500 ms, and only when the text changed. Each redraw re-probes the address, so a removed screen is noticed and a re-attached one is re-initialised.
- Build flags:
  - `-D ML_DISPLAY_ENABLED=0` stops the firmware from touching the I2C pins at all.
  - `-D ML_DISPLAY_SDA=<gpio> -D ML_DISPLAY_SCL=<gpio>` selects other pins.

## What it shows

72×40 (default):

```
MissionLink
USB+ BLE 1        USB host connected (+/-); BLE client count, or adv/off
LoRa RX on        or: off / pins unverified / RX error / ...
Rx12 -97dBm       packets received and last RSSI (or: Rx 0)
TXoff client      RF transmit gate and node preset
```

128×64 adds the firmware version, the last SNR and longer labels (`USB: host connected`, `BLE: advertising`, `LoRa: RX listening`).

"USB" uses the native USB-Serial/JTAG connection state. "TXoff" reflects the compile-time `ML_RF_ENABLED` gate. The text layout lives in `src/display_format.cpp` and is covered by `test/test_display_format`.

The USB/BLE command protocol is unchanged; the screen is display-only.
