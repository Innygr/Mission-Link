#pragma once
#include <stdint.h>
#include <stddef.h>
#include "missionlink_packet.h"
namespace ml {
enum class MeshAction : uint8_t { DropInvalid, DropDuplicate, DeliverLocal, DeliverAndForward, ForwardOnly };
enum class NodePreset : uint8_t { Client, Repeater, Gateway };
const char* presetName(NodePreset preset);
bool parsePreset(const char* name, NodePreset& out);
class MeshRouter {
 public:
  static constexpr size_t DUPLICATE_CACHE_SIZE = 64;
  static constexpr uint32_t DUPLICATE_TTL_MS = 60000;
  static constexpr uint32_t RATE_WINDOW_MS = 1000;
  static constexpr uint8_t MAX_FORWARDS_PER_WINDOW = 8;
  static constexpr uint8_t MAX_FORWARDS_PER_SOURCE_WINDOW = 3;
  static constexpr size_t SOURCE_BUCKETS = 8;
  MeshRouter();
  MeshAction process(const Packet& incoming, const uint8_t localId[8], uint32_t nowMs, Packet& forwarded);
  void reset();
 private:
  struct SeenEntry { uint8_t source[8]; uint8_t messageId[8]; uint32_t seenAt; bool valid; };
  struct SourceBucket { uint8_t source[8]; uint32_t windowStart; uint8_t forwards; bool valid; };
  SeenEntry seen_[DUPLICATE_CACHE_SIZE];
  SourceBucket sources_[SOURCE_BUCKETS];
  size_t nextSeen_, nextSource_;
  uint32_t globalWindowStart_;
  uint8_t globalForwards_;
  bool globalWindowValid_;
  bool isDuplicate(const Packet&, uint32_t);
  bool allowForward(const Packet&, uint32_t);
};
}
