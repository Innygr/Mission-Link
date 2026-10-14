#include "missionlink_display.h"
#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <string.h>

// Default to the board's I2C pins (XIAO ESP32-S3: SDA=GPIO5/D4, SCL=GPIO6/D5, which
// do not overlap the Wio-SX1262 pins). Override with -D ML_DISPLAY_SDA=.. -D ML_DISPLAY_SCL=..
#ifndef ML_DISPLAY_SDA
#define ML_DISPLAY_SDA SDA
#endif
#ifndef ML_DISPLAY_SCL
#define ML_DISPLAY_SCL SCL
#endif
// Default screen: the XIAO ML Kit's 0.42" 72x40 SSD1306. Set -D ML_DISPLAY_128X64=1 for the
// 0.96" 128x64 SSD1306 on Seeed's XIAO expansion board. Set -D ML_DISPLAY_ENABLED=0 to never
// touch the I2C pins.
#ifndef ML_DISPLAY_ENABLED
#define ML_DISPLAY_ENABLED 1
#endif

namespace ml {
namespace {
constexpr uint8_t kCandidateAddresses[] = {0x3C, 0x3D};  // SSD1306 7-bit addresses
constexpr uint32_t kReprobeAbsentMs = 5000;  // look for a newly attached screen
constexpr uint32_t kRedrawMs = 500;          // also re-checks that the screen is still there
#if ML_DISPLAY_128X64
U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);
constexpr DisplayLayout kLayout = DisplayLayout::Wide128x64;
const uint8_t* const kFont = u8g2_font_6x10_tf;
constexpr int kFirstBaseline = 10, kLineHeight = 10;
#else
// Rotated 180 degrees, as in the maker100 XIAO ML Kit sketches.
U8G2_SSD1306_72X40_ER_F_HW_I2C oled(U8G2_R2, U8X8_PIN_NONE);
constexpr DisplayLayout kLayout = DisplayLayout::Compact72x40;
const uint8_t* const kFont = u8g2_font_5x7_tf;
constexpr int kFirstBaseline = 6, kLineHeight = 8;  // 5x7 font: 6 px ascent, 1 px descent; last row ends at y=39
#endif
bool wireStarted = false;
}  // namespace

bool StatusDisplay::probe() {
  if (!wireStarted) {
    Wire.begin(ML_DISPLAY_SDA, ML_DISPLAY_SCL);
    Wire.setTimeOut(20);
    wireStarted = true;
  }
  for (uint8_t addr : kCandidateAddresses) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      if (addr != address_) {
        address_ = addr;
        oled.setI2CAddress(addr << 1);  // U8g2 takes the 8-bit form
        oled.setBusClock(400000);
        oled.begin();
        oled.setFont(kFont);
        memset(shown_, 0, sizeof(shown_));  // force a full redraw on the new screen
      }
      return true;
    }
  }
  address_ = 0;
  return false;
}

void StatusDisplay::begin(uint32_t nowMs) {
#if ML_DISPLAY_ENABLED
  lastProbeMs_ = nowMs;
  probe();
#else
  (void)nowMs;
#endif
}

void StatusDisplay::update(const ConnectivitySnapshot& snapshot, uint32_t nowMs) {
#if ML_DISPLAY_ENABLED
  if (!present()) {
    if (nowMs - lastProbeMs_ < kReprobeAbsentMs) return;
    lastProbeMs_ = nowMs;
    if (!probe()) return;
  }
  if (nowMs - lastDrawMs_ < kRedrawMs) return;
  lastDrawMs_ = nowMs;
  if (!probe()) return;  // screen was removed

  char rows[kDisplayRows][kDisplayCols + 1];
  formatStatusLines(snapshot, kLayout, rows);
  if (memcmp(rows, shown_, sizeof(rows)) == 0) return;
  memcpy(shown_, rows, sizeof(rows));

  oled.clearBuffer();
  for (size_t i = 0; i < displayGeometry(kLayout).rows; ++i) {
    oled.drawStr(0, kFirstBaseline + static_cast<int>(i) * kLineHeight, rows[i]);
  }
  oled.sendBuffer();
#else
  (void)snapshot;
  (void)nowMs;
#endif
}

}  // namespace ml
