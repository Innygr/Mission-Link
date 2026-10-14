#include <unity.h>
#include "missionlink_packet.h"
void test_round_trip(){
 ml::Packet p;p.type=ml::PacketType::Data;p.mode=ml::AddressMode::Group;p.source[0]=0x12;p.destination[0]=0x34;p.messageId[7]=0x99;p.payload={'h','i'};
 std::vector<uint8_t> bytes;TEST_ASSERT_TRUE(ml::encode(p,bytes));ml::Packet q;TEST_ASSERT_TRUE(ml::decode(bytes.data(),bytes.size(),q));
 TEST_ASSERT_EQUAL_UINT8((uint8_t)p.mode,(uint8_t)q.mode);TEST_ASSERT_EQUAL_UINT8(p.source[0],q.source[0]);TEST_ASSERT_EQUAL_UINT8(p.destination[0],q.destination[0]);TEST_ASSERT_EQUAL_UINT8(p.messageId[7],q.messageId[7]);TEST_ASSERT_EQUAL_UINT32(p.payload.size(),q.payload.size());TEST_ASSERT_EQUAL_UINT8('h',q.payload[0]);
}
void test_reject_truncated(){uint8_t bad[]={1,2,0};ml::Packet q;TEST_ASSERT_FALSE(ml::decode(bad,sizeof(bad),q));}
void test_reject_invalid_hops(){ml::Packet p;p.hopLimit=1;p.hopCount=2;std::vector<uint8_t> bytes;TEST_ASSERT_FALSE(ml::encode(p,bytes));}
int main(int argc,char** argv){UNITY_BEGIN();RUN_TEST(test_round_trip);RUN_TEST(test_reject_truncated);RUN_TEST(test_reject_invalid_hops);return UNITY_END();}
