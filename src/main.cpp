#include <Arduino.h>
#include <NimBLEDevice.h>
#include "missionlink_config.h"
static const char* BLE_NAME="MissionLink";
static const char* SERVICE_UUID="3f4a0001-7c2e-4a5b-9d11-5b7d6e100001";
static const char* RX_UUID="3f4a0002-7c2e-4a5b-9d11-5b7d6e100001";
static const char* TX_UUID="3f4a0003-7c2e-4a5b-9d11-5b7d6e100001";
static NimBLECharacteristic* txChar=nullptr;
static String commandBuffer;
static void report(const String& s){
 Serial.println(s);
 if(txChar&&txChar->getSubscribedCount()>0){txChar->setValue(s.c_str());txChar->notify();}
}
static void dispatchCommand(String cmd){
 cmd.trim();
 if(cmd=="help")report("help | status | nodes | send <node-id> <text> | group <channel-id> <text> | join <channel-id> | leave <channel-id>");
 else if(cmd=="status")report(String("MissionLink 0.1.0; serial+BLE; RF=")+(ML_RF_ENABLED?"enabled":"disabled"));
 else if(cmd=="nodes")report("Node discovery not implemented yet.");
 else if(cmd.startsWith("send "))report("Direct send unavailable until radio and encryption are implemented.");
 else if(cmd.startsWith("group "))report("Group send unavailable until group-key encryption and radio are implemented.");
 else if(cmd.startsWith("join "))report("Channel membership and key provisioning not implemented yet.");
 else if(cmd.startsWith("leave "))report("Channel membership changes not implemented yet.");
 else report("ERR unknown command; type help");
}
class RxCallbacks:public NimBLECharacteristicCallbacks{
 void onWrite(NimBLECharacteristic* c,NimBLEConnInfo& info) override{
  std::string value=c->getValue();if(!value.empty())dispatchCommand(String(value.c_str()));
 }
};
void setup(){
 Serial.begin(115200);delay(300);
 Serial.println("\nMissionLink 0.1.0 starting; RF deliberately disabled.");
 Serial.println("Type 'help' for commands.");
 NimBLEDevice::init(BLE_NAME);auto* server=NimBLEDevice::createServer();auto* service=server->createService(SERVICE_UUID);
 auto* rx=service->createCharacteristic(RX_UUID,NIMBLE_PROPERTY::WRITE|NIMBLE_PROPERTY::WRITE_NR);
 txChar=service->createCharacteristic(TX_UUID,NIMBLE_PROPERTY::READ|NIMBLE_PROPERTY::NOTIFY);
 rx->setCallbacks(new RxCallbacks());txChar->setValue("MissionLink ready");service->start();
 NimBLEDevice::getAdvertising()->addServiceUUID(SERVICE_UUID);NimBLEDevice::getAdvertising()->start();
 Serial.println("BLE advertising as MissionLink");
}
void loop(){
 while(Serial.available()){
  char ch=(char)Serial.read();
  if(ch=='\n'||ch=='\r'){if(commandBuffer.length()){dispatchCommand(commandBuffer);commandBuffer="";}}
  else if(commandBuffer.length()<256)commandBuffer+=ch;
 }
 delay(5);
}
