#pragma once
#include <stdint.h>

// Verify exact Seeed Wio-SX1262 revision/pinout before enabling RF.
#define ML_RF_ENABLED 0
static constexpr uint8_t ML_PROTOCOL_VERSION = 1;
static constexpr uint8_t ML_MAX_HOPS = 4;
static constexpr uint16_t ML_MAX_PAYLOAD = 180;
static constexpr uint8_t ML_NODE_ID_BYTES = 8;
static constexpr uint8_t ML_MESSAGE_ID_BYTES = 8;
static constexpr uint8_t ML_GROUP_ID_BYTES = 4;
static constexpr uint16_t ML_DEFAULT_CHANNEL = 1;
