# Optional status screen

If a 128×64 **SSD1306** I2C OLED is attached, the firmware shows live connectivity on it. Without one, nothing changes.

## Detection

- At boot, and every 5 s while no screen is found, the firmware probes I2C addresses `0x3C` and `0x3D` on the board's default pins: XIAO ESP32-S3 `SDA = GPIO5 (D4)`, `SCL = GPIO6 (D5)`. These don't overlap the Wio-SX1262 pins in `platformio.ini`.
- If an address acknowledges, the screen is initialised. It is redrawn at most every 500 ms, and only when the text changed. Each redraw re-probes the address, so a removed screen is noticed and a re-attached one is re-initialised.
- Build flags:
  - `-D ML_DISPLAY_ENABLED=0` stops the firmware from touching the I2C pins at all.
  - `-D ML_DISPLAY_SDA=<gpio> -D ML_DISPLAY_SCL=<gpio>` selects other pins.

**Assumption:** the screen is an SSD1306 controller, as on Seeed's XIAO expansion board. An SH1106-based 1.3" OLED at the same address would be detected but show a shifted image; it would need a different U8g2 constructor.

## What it shows

```
MissionLink 0.2.1
USB: host connected      (or: no host)
BLE: 1 client            (or: advertising / off)
LoRa: RX listening       (or: off / pins unverified / RX error / ...)
Rx 12 -97dBm -3dB        (packets received, last RSSI/SNR; or: Rx 0 pkts)
TX off client            (RF transmit gate, node preset)
```

"USB: host connected" uses the native USB-Serial/JTAG connection state. "TX off" reflects the compile-time `ML_RF_ENABLED` gate. The text layout lives in `src/display_format.cpp` and is covered by `test/test_display_format`.

The USB/BLE command protocol is unchanged; the screen is display-only.
