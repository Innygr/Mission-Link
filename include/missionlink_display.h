#pragma once
#include <stddef.h>
#include <stdint.h>

namespace ml {

// Everything the status screen shows. Filled in by main.cpp; the display code
// never queries BLE, USB, or the radio itself.
struct ConnectivitySnapshot {
  const char* firmware;
  bool usbHostConnected;
  bool bleAdvertising;
  uint8_t bleClients;
  bool radioInitialized;
  bool radioReceiving;
  const char* radioState;   // same names as the "status" command's radioState
  bool hasSignal;           // true once a packet has been received
  int16_t lastRssi;
  int8_t lastSnr;
  uint32_t packetsReceived;
  bool rfTransmitEnabled;
  const char* preset;
};

enum class DisplayLayout : uint8_t {
  Compact72x40,  // XIAO ML Kit 0.42" SSD1306, 5x7 font: 5 rows x 14 characters (default)
  Wide128x64,    // XIAO expansion board 0.96" SSD1306, 6x10 font: 6 rows x 21 characters
};

// Buffer size large enough for either layout.
static constexpr size_t kDisplayRows = 6;
static constexpr size_t kDisplayCols = 21;

struct DisplayGeometry {
  size_t rows;
  size_t cols;
};
DisplayGeometry displayGeometry(DisplayLayout layout);

// Pure text layout for the status screen (host-testable). Fills displayGeometry(layout).rows
// rows, each NUL-terminated and truncated to displayGeometry(layout).cols characters.
void formatStatusLines(const ConnectivitySnapshot& s, DisplayLayout layout,
                       char rows[kDisplayRows][kDisplayCols + 1]);

// Optional I2C OLED status screen. Probes for an SSD1306 at 0x3C/0x3D; if nothing
// answers, it stays inactive and re-probes occasionally so a screen attached later is found.
class StatusDisplay {
 public:
  void begin(uint32_t nowMs);
  // Call from loop(); redraws at most a few times per second and only when the text changed.
  void update(const ConnectivitySnapshot& snapshot, uint32_t nowMs);
  bool present() const { return address_ != 0; }
  uint8_t address() const { return address_; }

 private:
  bool probe();
  uint8_t address_ = 0;
  uint32_t lastProbeMs_ = 0;
  uint32_t lastDrawMs_ = 0;
  char shown_[kDisplayRows][kDisplayCols + 1] = {};
};

}  // namespace ml
