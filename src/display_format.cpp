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
}  // namespace

void formatStatusLines(const ConnectivitySnapshot& s, char rows[kDisplayRows][kDisplayCols + 1]) {
  const size_t n = kDisplayCols + 1;  // snprintf truncates to the row width
  snprintf(rows[0], n, "MissionLink %s", s.firmware ? s.firmware : "?");
  snprintf(rows[1], n, "USB: %s", s.usbHostConnected ? "host connected" : "no host");

  if (s.bleClients > 0) {
    snprintf(rows[2], n, "BLE: %u client%s", static_cast<unsigned>(s.bleClients), s.bleClients == 1 ? "" : "s");
  } else {
    snprintf(rows[2], n, "BLE: %s", s.bleAdvertising ? "advertising" : "off");
  }

  if (s.radioInitialized && s.radioReceiving) {
    snprintf(rows[3], n, "LoRa: RX listening");
  } else if (!s.radioInitialized && s.radioState && strcmp(s.radioState, "disabled") == 0) {
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

}  // namespace ml
