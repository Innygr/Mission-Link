#include "missionlink_packet.h"
#include "missionlink_config.h"
#include <algorithm>

namespace ml {
static constexpr size_t HEADER_SIZE = 32;

static void put16(std::vector<uint8_t>& out, uint16_t value) {
  out.push_back(static_cast<uint8_t>(value >> 8));
  out.push_back(static_cast<uint8_t>(value));
}

static uint16_t get16(const uint8_t* data) {
  return (static_cast<uint16_t>(data[0]) << 8) | data[1];
}

bool encode(const Packet& packet, std::vector<uint8_t>& out) {
  // Never leave a previous valid frame in the output after a failed encode.
  out.clear();
  if (packet.version != ML_PROTOCOL_VERSION ||
      packet.payload.size() > ML_MAX_PAYLOAD) return false;
  if (static_cast<uint8_t>(packet.type) < static_cast<uint8_t>(PacketType::Hello) ||
      static_cast<uint8_t>(packet.type) > static_cast<uint8_t>(PacketType::Leave)) return false;
  if (static_cast<uint8_t>(packet.mode) > static_cast<uint8_t>(AddressMode::Broadcast)) return false;
  if (packet.hopCount > packet.hopLimit || packet.hopLimit > ML_MAX_HOPS) return false;

  out.reserve(HEADER_SIZE + packet.payload.size());
  out.push_back(packet.version);
  out.push_back(static_cast<uint8_t>(packet.type));
  out.push_back(static_cast<uint8_t>(packet.mode));
  out.push_back(packet.flags);
  out.insert(out.end(), packet.source, packet.source + ML_NODE_ID_BYTES);
  out.insert(out.end(), packet.destination, packet.destination + ML_NODE_ID_BYTES);
  out.insert(out.end(), packet.messageId, packet.messageId + ML_MESSAGE_ID_BYTES);
  out.push_back(packet.hopLimit);
  out.push_back(packet.hopCount);
  put16(out, static_cast<uint16_t>(packet.payload.size()));
  out.insert(out.end(), packet.payload.begin(), packet.payload.end());
  return true;
}

bool decode(const uint8_t* data, size_t len, Packet& out) {
  if (!data || len < HEADER_SIZE || data[0] != ML_PROTOCOL_VERSION) return false;
  if (data[1] < static_cast<uint8_t>(PacketType::Hello) ||
      data[1] > static_cast<uint8_t>(PacketType::Leave) ||
      data[2] > static_cast<uint8_t>(AddressMode::Broadcast)) return false;

  const uint8_t hopLimit = data[28];
  const uint8_t hopCount = data[29];
  const uint16_t payloadLen = get16(data + 30);
  if (hopLimit > ML_MAX_HOPS || hopCount > hopLimit ||
      payloadLen > ML_MAX_PAYLOAD || len != HEADER_SIZE + payloadLen) return false;

  out.version = data[0];
  out.type = static_cast<PacketType>(data[1]);
  out.mode = static_cast<AddressMode>(data[2]);
  out.flags = data[3];
  size_t pos = 4;
  std::copy(data + pos, data + pos + ML_NODE_ID_BYTES, out.source);
  pos += ML_NODE_ID_BYTES;
  std::copy(data + pos, data + pos + ML_NODE_ID_BYTES, out.destination);
  pos += ML_NODE_ID_BYTES;
  std::copy(data + pos, data + pos + ML_MESSAGE_ID_BYTES, out.messageId);
  out.hopLimit = hopLimit;
  out.hopCount = hopCount;
  out.payload.assign(data + HEADER_SIZE, data + len);
  return true;
}

std::string hexId(const uint8_t* id, size_t n) {
  if (!id && n) return {};
  static const char* hex = "0123456789abcdef";
  std::string out;
  out.reserve(n * 2);
  for (size_t i = 0; i < n; ++i) {
    out.push_back(hex[id[i] >> 4]);
    out.push_back(hex[id[i] & 0x0f]);
  }
  return out;
}
} // namespace ml
