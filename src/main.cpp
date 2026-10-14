#include <Arduino.h>
#include <NimBLEDevice.h>
#include "missionlink_config.h"

static const char* BLE_NAME = "MissionLink";
static const char* SERVICE_UUID = "3f4a0001-7c2e-4a5b-9d11-5b7d6e100001";
static const char* RX_UUID = "3f4a0002-7c2e-4a5b-9d11-5b7d6e100001";
static const char* TX_UUID = "3f4a0003-7c2e-4a5b-9d11-5b7d6e100001";
static NimBLECharacteristic* txChar = nullptr;
static String commandBuffer;

static void report(const String& jsonLine) {
  Serial.println(jsonLine);
  if (txChar && txChar->getSubscribedCount() > 0) {
    txChar->setValue(jsonLine.c_str());
    txChar->notify();
  }
}

static void reportError(const char* code, const char* message) {
  String out = "{\"type\":\"error\",\"code\":\"";
  out += code;
  out += "\",\"message\":\"";
  out += message;
  out += "\"}";
  report(out);
}

static void dispatchCommand(String cmd) {
  cmd.trim();
  if (cmd == "help") {
    report("{\"type\":\"help\",\"commands\":[\"help\",\"status\",\"nodes\",\"send <node-id> <text>\",\"group <channel-id> <text>\",\"join <channel-id>\",\"leave <channel-id>\"]}");
  } else if (cmd == "status") {
    String out = "{\"type\":\"status\",\"firmware\":\"0.2.0\",\"protocolVersion\":";
    out += String(ML_PROTOCOL_VERSION);
    out += ",\"rfEnabled\":";
    out += ML_RF_ENABLED ? "true" : "false";
    out += ",\"bleReady\":true,\"serialReady\":true,\"radioReady\":false}";
    report(out);
  } else if (cmd == "nodes") {
    report("{\"type\":\"nodes\",\"items\":[],\"ready\":false,\"reason\":\"discovery_not_implemented\"}");
  } else if (cmd.startsWith("send ")) {
    reportError("not_ready", "Direct messaging is unavailable until radio and encryption are implemented.");
  } else if (cmd.startsWith("group ")) {
    reportError("not_ready", "Group messaging is unavailable until group keys and radio are implemented.");
  } else if (cmd.startsWith("join ")) {
    reportError("not_ready", "Channel membership and key provisioning are not implemented.");
  } else if (cmd.startsWith("leave ")) {
    reportError("not_ready", "Channel membership is not implemented.");
  } else if (cmd.length() == 0) {
    return;
  } else {
    reportError("unknown_command", "Unknown command. Send help for available commands.");
  }
}

class RxCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* characteristic, NimBLEConnInfo& info) override {
    std::string value = characteristic->getValue();
    if (!value.empty()) dispatchCommand(String(value.c_str()));
  }
};

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("{\"type\":\"boot\",\"firmware\":\"0.2.0\",\"rfEnabled\":false}");
  Serial.println("{\"type\":\"hint\",\"message\":\"Send help for commands. RF is deliberately disabled.\"}");

  NimBLEDevice::init(BLE_NAME);
  auto* server = NimBLEDevice::createServer();
  auto* service = server->createService(SERVICE_UUID);
  auto* rx = service->createCharacteristic(
      RX_UUID, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  txChar = service->createCharacteristic(
      TX_UUID, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  rx->setCallbacks(new RxCallbacks());
  txChar->setValue("{\"type\":\"ready\",\"firmware\":\"0.2.0\",\"rfEnabled\":false}");
  service->start();
  NimBLEDevice::getAdvertising()->addServiceUUID(SERVICE_UUID);
  NimBLEDevice::getAdvertising()->start();
  Serial.println("{\"type\":\"ble\",\"advertising\":true}");
}

void loop() {
  while (Serial.available()) {
    char ch = static_cast<char>(Serial.read());
    if (ch == '\n' || ch == '\r') {
      if (commandBuffer.length()) {
        dispatchCommand(commandBuffer);
        commandBuffer = "";
      }
    } else if (commandBuffer.length() < 256) {
      commandBuffer += ch;
    }
  }
  delay(5);
}
