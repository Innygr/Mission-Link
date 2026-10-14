#include "missionlink_display.h"
#include <stdio.h>
#include <string.h>

namespace ml {
namespace {
// Short screen labels for the "status" command's radioState names.
const char* shortRadioState(const char* state) {
  if (!state) return "?";
  if (strcmp(state, "pinmap_unverified") == 0) return "pins unverified";
  if (strcmp(state, "receive_error") == 0) return "RX error";
  if (strcmp(state, "decode_error") == 0) return "decode error";
  if (strcmp(state, "transmit_blocked") == 0) return "TX blocked";
  if (strcmp(state, "transmit_error") == 0) return "TX error";
  return state;
}

bool radioOff(const ConnectivitySnapshot& s) {
  return !s.radioInitialized && s.radioState && strcmp(s.radioState, "disabled") == 0;
}

// 5 rows x 14 characters for the 72x40 panel.
void formatCompact(const ConnectivitySnapshot& s, char rows[kDisplayRows][kDisplayCols + 1], size_t n) {
  snprintf(rows[0], n, "MissionLink");
  if (s.bleClients > 0) {
    snprintf(rows[1], n, "USB%s BLE %u", s.usbHostConnected ? "+" : "-", static_cast<unsigned>(s.bleClients));
  } else {
    snprintf(rows[1], n, "USB%s BLE %s", s.usbHostConnected ? "+" : "-", s.bleAdvertising ? "adv" : "off");
  }
  if (s.radioInitialized && s.radioReceiving) {
    snprintf(rows[2], n, "LoRa RX on");
  } else if (radioOff(s)) {
    snprintf(rows[2], n, "LoRa off");
  } else {
    snprintf(rows[2], n, "LoRa %s", shortRadioState(s.radioState));
  }
  if (s.hasSignal) {
    snprintf(rows[3], n, "Rx%lu %ddBm", static_cast<unsigned long>(s.packetsReceived), static_cast<int>(s.lastRssi));
  } else {
    snprintf(rows[3], n, "Rx 0");
  }
  snprintf(rows[4], n, "TX%s %s", s.rfTransmitEnabled ? "ON" : "off", s.preset ? s.preset : "");
}

// 6 rows x 21 characters for the 128x64 panel.
void formatWide(const ConnectivitySnapshot& s, char rows[kDisplayRows][kDisplayCols + 1], size_t n) {
  snprintf(rows[0], n, "MissionLink %s", s.firmware ? s.firmware : "?");
  snprintf(rows[1], n, "USB: %s", s.usbHostConnected ? "host connected" : "no host");
  if (s.bleClients > 0) {
    snprintf(rows[2], n, "BLE: %u client%s", static_cast<unsigned>(s.bleClients), s.bleClients == 1 ? "" : "s");
  } else {
    snprintf(rows[2], n, "BLE: %s", s.bleAdvertising ? "advertising" : "off");
  }
  if (s.radioInitialized && s.radioReceiving) {
    snprintf(rows[3], n, "LoRa: RX listening");
  } else if (radioOff(s)) {
    snprintf(rows[3], n, "LoRa: off");
  } else {
    snprintf(rows[3], n, "LoRa: %s", shortRadioState(s.radioState));
  }
  if (s.hasSignal) {
    snprintf(rows[4], n, "Rx %lu %ddBm %ddB", static_cast<unsigned long>(s.packetsReceived),
             static_cast<int>(s.lastRssi), static_cast<int>(s.lastSnr));
  } else {
    snprintf(rows[4], n, "Rx 0 pkts");
  }
  snprintf(rows[5], n, "TX %s %s", s.rfTransmitEnabled ? "ON" : "off", s.preset ? s.preset : "");
}
}  // namespace

DisplayGeometry displayGeometry(DisplayLayout layout) {
  return layout == DisplayLayout::Wide128x64 ? DisplayGeometry{6, 21} : DisplayGeometry{5, 14};
}

void formatStatusLines(const ConnectivitySnapshot& s, DisplayLayout layout,
                       char rows[kDisplayRows][kDisplayCols + 1]) {
  memset(rows, 0, kDisplayRows * (kDisplayCols + 1));  // whole buffer: callers compare it with memcmp
  const size_t n = displayGeometry(layout).cols + 1;  // snprintf truncates to the row width
  if (layout == DisplayLayout::Wide128x64) formatWide(s, rows, n);
  else formatCompact(s, rows, n);
}

}  // namespace ml
