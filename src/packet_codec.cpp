#include "missionlink_packet.h"
#include "missionlink_config.h"
#include <algorithm>
namespace ml {
static constexpr size_t HEADER_SIZE=32;
static void put16(std::vector<uint8_t>& o,uint16_t v){o.push_back((uint8_t)(v>>8));o.push_back((uint8_t)v);}
static uint16_t get16(const uint8_t* p){return (uint16_t(p[0])<<8)|p[1];}
bool encode(const Packet& p,std::vector<uint8_t>& out){
 if(p.version!=ML_PROTOCOL_VERSION||p.payload.size()>ML_MAX_PAYLOAD)return false;
 if((uint8_t)p.type<(uint8_t)PacketType::Hello||(uint8_t)p.type>(uint8_t)PacketType::Leave)return false;
 if((uint8_t)p.mode>(uint8_t)AddressMode::Broadcast)return false;
 if(p.hopCount>p.hopLimit||p.hopLimit>ML_MAX_HOPS)return false;
 out.clear();out.reserve(HEADER_SIZE+p.payload.size());
 out.push_back(p.version);out.push_back((uint8_t)p.type);out.push_back((uint8_t)p.mode);out.push_back(p.flags);
 out.insert(out.end(),p.source,p.source+8);out.insert(out.end(),p.destination,p.destination+8);out.insert(out.end(),p.messageId,p.messageId+8);
 out.push_back(p.hopLimit);out.push_back(p.hopCount);put16(out,(uint16_t)p.payload.size());
 out.insert(out.end(),p.payload.begin(),p.payload.end());return true;
}
bool decode(const uint8_t* data,size_t len,Packet& out){
 if(!data||len<HEADER_SIZE||data[0]!=ML_PROTOCOL_VERSION)return false;
 if(data[1]<(uint8_t)PacketType::Hello||data[1]>(uint8_t)PacketType::Leave||data[2]>(uint8_t)AddressMode::Broadcast)return false;
 uint8_t hopLimit=data[28],hopCount=data[29];uint16_t payloadLen=get16(data+30);
 if(hopLimit>ML_MAX_HOPS||hopCount>hopLimit||payloadLen>ML_MAX_PAYLOAD||len!=HEADER_SIZE+payloadLen)return false;
 out.version=data[0];out.type=(PacketType)data[1];out.mode=(AddressMode)data[2];out.flags=data[3];
 size_t pos=4;std::copy(data+pos,data+pos+8,out.source);pos+=8;std::copy(data+pos,data+pos+8,out.destination);pos+=8;std::copy(data+pos,data+pos+8,out.messageId);
 out.hopLimit=hopLimit;out.hopCount=hopCount;out.payload.assign(data+HEADER_SIZE,data+len);return true;
}
std::string hexId(const uint8_t* id,size_t n){if(!id&&n)return {};static const char* h="0123456789abcdef";std::string s;s.reserve(n*2);for(size_t i=0;i<n;i++){s.push_back(h[id[i]>>4]);s.push_back(h[id[i]&15]);}return s;}
}
