#include <unity.h>
#include "missionlink_packet.h"
#include "missionlink_config.h"

void test_round_trip() {
  ml::Packet p;
  p.type = ml::PacketType::Data;
  p.mode = ml::AddressMode::Group;
  p.source[0] = 0x12;
  p.destination[0] = 0x34;
  p.messageId[7] = 0x99;
  p.hopLimit = 4;
  p.hopCount = 2;
  p.flags = 0xa5;
  p.payload = {'h', 'i'};
  std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes));
  ml::Packet q;
  TEST_ASSERT_TRUE(ml::decode(bytes.data(), bytes.size(), q));
  TEST_ASSERT_EQUAL_UINT8((uint8_t)p.type, (uint8_t)q.type);
  TEST_ASSERT_EQUAL_UINT8((uint8_t)p.mode, (uint8_t)q.mode);
  TEST_ASSERT_EQUAL_UINT8(p.flags, q.flags);
  TEST_ASSERT_EQUAL_UINT8(p.source[0], q.source[0]);
  TEST_ASSERT_EQUAL_UINT8(p.destination[0], q.destination[0]);
  TEST_ASSERT_EQUAL_UINT8(p.messageId[7], q.messageId[7]);
  TEST_ASSERT_EQUAL_UINT8(p.hopLimit, q.hopLimit);
  TEST_ASSERT_EQUAL_UINT8(p.hopCount, q.hopCount);
  TEST_ASSERT_EQUAL_UINT32(p.payload.size(), q.payload.size());
  TEST_ASSERT_EQUAL_UINT8('h', q.payload[0]);
}
void test_reject_truncated() {
  uint8_t bad[] = {1, 2, 0};
  ml::Packet q;
  TEST_ASSERT_FALSE(ml::decode(bad, sizeof(bad), q));
}
void test_reject_null_input() {
  ml::Packet q;
  TEST_ASSERT_FALSE(ml::decode(nullptr, 32, q));
}
void test_reject_invalid_hops() {
  ml::Packet p; p.hopLimit = 1; p.hopCount = 2;
  std::vector<uint8_t> bytes;
  TEST_ASSERT_FALSE(ml::encode(p, bytes));
}
void test_reject_invalid_type_on_encode() {
  ml::Packet p; p.type = (ml::PacketType)99;
  std::vector<uint8_t> bytes;
  TEST_ASSERT_FALSE(ml::encode(p, bytes));
}
void test_reject_invalid_mode_on_encode() {
  ml::Packet p; p.mode = (ml::AddressMode)99;
  std::vector<uint8_t> bytes;
  TEST_ASSERT_FALSE(ml::encode(p, bytes));
}
void test_reject_oversized_payload() {
  ml::Packet p; p.payload.resize(ML_MAX_PAYLOAD + 1, 0);
  std::vector<uint8_t> bytes;
  TEST_ASSERT_FALSE(ml::encode(p, bytes));
}
void test_encode_failure_clears_stale_output() {
  ml::Packet p;
  std::vector<uint8_t> bytes = {0xde, 0xad};
  p.version = 99;
  TEST_ASSERT_FALSE(ml::encode(p, bytes));
  TEST_ASSERT_TRUE(bytes.empty());
}
void test_max_payload_round_trip() {
  ml::Packet p;
  p.payload.resize(ML_MAX_PAYLOAD);
  for (size_t i = 0; i < p.payload.size(); ++i) p.payload[i] = (uint8_t)i;
  std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes));
  TEST_ASSERT_EQUAL_UINT32(32 + ML_MAX_PAYLOAD, bytes.size());
  ml::Packet decoded;
  TEST_ASSERT_TRUE(ml::decode(bytes.data(), bytes.size(), decoded));
  TEST_ASSERT_EQUAL_UINT32(ML_MAX_PAYLOAD, decoded.payload.size());
  TEST_ASSERT_EQUAL_UINT8(p.payload.back(), decoded.payload.back());
}
void test_decode_rejects_unknown_version() {
  ml::Packet p; std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes)); bytes[0] = 2;
  ml::Packet q; TEST_ASSERT_FALSE(ml::decode(bytes.data(), bytes.size(), q));
}
void test_decode_rejects_invalid_type() {
  ml::Packet p; std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes)); bytes[1] = 99;
  ml::Packet q; TEST_ASSERT_FALSE(ml::decode(bytes.data(), bytes.size(), q));
}
void test_decode_rejects_invalid_mode() {
  ml::Packet p; std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes)); bytes[2] = 99;
  ml::Packet q; TEST_ASSERT_FALSE(ml::decode(bytes.data(), bytes.size(), q));
}
void test_decode_rejects_hop_limit_over_max() {
  ml::Packet p; std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes)); bytes[28] = ML_MAX_HOPS + 1;
  ml::Packet q; TEST_ASSERT_FALSE(ml::decode(bytes.data(), bytes.size(), q));
}
void test_decode_rejects_hop_count_over_limit() {
  ml::Packet p; std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes)); bytes[29] = 5;
  ml::Packet q; TEST_ASSERT_FALSE(ml::decode(bytes.data(), bytes.size(), q));
}
void test_decode_rejects_payload_length_mismatch() {
  ml::Packet p; p.payload = {'o', 'k'};
  std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes)); bytes[31] = 3;
  ml::Packet q; TEST_ASSERT_FALSE(ml::decode(bytes.data(), bytes.size(), q));
}
void test_decode_rejects_trailing_bytes() {
  ml::Packet p; std::vector<uint8_t> bytes;
  TEST_ASSERT_TRUE(ml::encode(p, bytes)); bytes.push_back(0);
  ml::Packet q; TEST_ASSERT_FALSE(ml::decode(bytes.data(), bytes.size(), q));
}
void test_hex_id_null_is_safe() {
  TEST_ASSERT_EQUAL_STRING("", ml::hexId(nullptr, 8).c_str());
}
int main(int argc, char** argv) {
  UNITY_BEGIN();
  RUN_TEST(test_round_trip);
  RUN_TEST(test_reject_truncated);
  RUN_TEST(test_reject_null_input);
  RUN_TEST(test_reject_invalid_hops);
  RUN_TEST(test_reject_invalid_type_on_encode);
  RUN_TEST(test_reject_invalid_mode_on_encode);
  RUN_TEST(test_reject_oversized_payload);
  RUN_TEST(test_encode_failure_clears_stale_output);
  RUN_TEST(test_max_payload_round_trip);
  RUN_TEST(test_decode_rejects_unknown_version);
  RUN_TEST(test_decode_rejects_invalid_type);
  RUN_TEST(test_decode_rejects_invalid_mode);
  RUN_TEST(test_decode_rejects_hop_limit_over_max);
  RUN_TEST(test_decode_rejects_hop_count_over_limit);
  RUN_TEST(test_decode_rejects_payload_length_mismatch);
  RUN_TEST(test_decode_rejects_trailing_bytes);
  RUN_TEST(test_hex_id_null_is_safe);
  return UNITY_END();
}
