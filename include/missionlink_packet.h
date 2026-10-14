#pragma once
#include <stdint.h>
#include <stddef.h>
#include <vector>
#include <string>
namespace ml {
enum class PacketType : uint8_t { Hello=1, Data=2, Ack=3, Status=4, Join=5, Leave=6 };
enum class AddressMode : uint8_t { Direct=0, Group=1, Broadcast=2 };
struct Packet {
  uint8_t version=1;
  PacketType type=PacketType::Data;
  AddressMode mode=AddressMode::Direct;
  uint8_t flags=0;
  uint8_t source[8]={};
  uint8_t destination[8]={};
  uint8_t messageId[8]={};
  uint8_t hopLimit=4;
  uint8_t hopCount=0;
  std::vector<uint8_t> payload; // Must be encrypted before radio TX.
};
bool encode(const Packet& p, std::vector<uint8_t>& out);
bool decode(const uint8_t* data, size_t len, Packet& out);
std::string hexId(const uint8_t* id, size_t n);
}
