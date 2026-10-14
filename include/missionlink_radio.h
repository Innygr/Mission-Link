#pragma once
#include <stddef.h>
#include <stdint.h>
#include "missionlink_packet.h"

namespace ml {
enum class RadioState : uint8_t {
  Disabled,
  PinmapUnverified,
  Ready,
  ReceiveError,
  DecodeError,
  TransmitBlocked,
  TransmitError
};

struct RadioStatus {
  RadioState state;
  bool initialized;
  bool receiving;
  int16_t lastRssi;
  int8_t lastSnr;
};

// RadioLib adapter for the SX1262. It is intentionally inert unless the exact
// board pin map has been verified and the appropriate feature flags are enabled.
class MissionLinkRadio {
 public:
  MissionLinkRadio();
  bool beginReceive();
  bool poll(Packet& packet);
  bool transmit(const Packet& packet);
  RadioStatus status() const;

 private:
  RadioState state_;
  bool initialized_;
  bool receiving_;
  int16_t lastRssi_;
  int8_t lastSnr_;
};
}
