#include <Arduino.h>
#include <NimBLEDevice.h>
#include <esp_mac.h>
#include "missionlink_config.h"
#include "mesh_router.h"
#include "missionlink_radio.h"

static const char* BLE_NAME = "MissionLink";
static const char* SERVICE_UUID = "3f4a0001-7c2e-4a5b-9d11-5b7d6e100001";
static const char* RX_UUID = "3f4a0002-7c2e-4a5b-9d11-5b7d6e100001";
static const char* TX_UUID = "3f4a0003-7c2e-4a5b-9d11-5b7d6e100001";
static constexpr size_t MAX_COMMAND_BYTES = 256;
static NimBLECharacteristic* txChar = nullptr;
static String commandBuffer;
static bool discardUntilNewline = false;
static ml::NodePreset activePreset = ml::NodePreset::Client;
static ml::MeshRouter meshRouter(activePreset);
static ml::MissionLinkRadio radioLink;
static uint8_t localNodeId[8] = {0};

static void report(const String& jsonLine) {
  Serial.println(jsonLine);
  if (txChar) {
    txChar->setValue(jsonLine.c_str());
    // NimBLE-Arduino 2.x handles the no-subscriber case in notify().
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
    report("{\"type\":\"help\",\"commands\":[\"help\",\"status\",\"nodes\",\"presets\",\"preset <client|repeater|gateway>\",\"send <node-id> <text>\",\"group <channel-id> <text>\",\"join <channel-id>\",\"leave <channel-id>\"]}");
  } else if (cmd == "presets") {
    report("{\"type\":\"presets\",\"items\":[{\"id\":\"client\",\"description\":\"End device; never relays packets.\"},{\"id\":\"repeater\",\"description\":\"Relays traffic without presenting group traffic locally.\"},{\"id\":\"gateway\",\"description\":\"Relays traffic and delivers group traffic locally.\"}]}");
  } else if (cmd.startsWith("preset ")) {
    String requested = cmd.substring(7);
    requested.trim();
    ml::NodePreset parsed;
    if (!ml::parsePreset(requested.c_str(), parsed)) {
      reportError("invalid_preset", "Use preset client, preset repeater, or preset gateway.");
      return;
    }
    activePreset = parsed;
    meshRouter.setPreset(activePreset);
    String out = "{\"type\":\"preset\",\"active\":\"";
    out += ml::presetName(activePreset);
    out += "\"}";
    report(out);
  } else if (cmd == "status") {
    const ml::RadioStatus radioStatus = radioLink.status();
    String out = "{\"type\":\"status\",\"firmware\":\"0.2.1\",\"protocolVersion\":";
    out += String(ML_PROTOCOL_VERSION);
    out += ",\"rfEnabled\":";
    out += ML_RF_ENABLED ? "true" : "false";
    out += ",\"bleReady\":true,\"serialReady\":true,\"radioReady\":false,\"preset\":\""; out += ml::presetName(activePreset); out += "\"}";
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
    if (value.empty()) return;
    if (value.size() > MAX_COMMAND_BYTES) {
      reportError("command_too_long", "Commands must be 256 bytes or fewer.");
      return;
    }
    dispatchCommand(String(value.c_str()));
  }
};

void setup() {
  Serial.begin(115200);
  delay(300);
  commandBuffer.reserve(MAX_COMMAND_BYTES);
  Serial.println();
  Serial.println("{\"type\":\"boot\",\"firmware\":\"0.2.1\",\"rfEnabled\":false}");
  Serial.println("{\"type\":\"hint\",\"message\":\"Send help for commands. RF is deliberately disabled.\"}");

  uint8_t mac[6] = {0};
  if (esp_read_mac(mac, ESP_MAC_WIFI_STA) == ESP_OK) {
    localNodeId[0] = 'M'; localNodeId[1] = 'L';
    for (size_t i = 0; i < 6; ++i) localNodeId[i + 2] = mac[i];
  }
  // Safe no-op while the verified pin map and radio feature flags are disabled.
  radioLink.beginReceive();

  NimBLEDevice::init(BLE_NAME);
  auto* server = NimBLEDevice::createServer();
  auto* service = server->createService(SERVICE_UUID);
  auto* rx = service->createCharacteristic(
      RX_UUID, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  txChar = service->createCharacteristic(
      TX_UUID, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  rx->setCallbacks(new RxCallbacks());
  txChar->setValue("{\"type\":\"ready\",\"firmware\":\"0.2.1\",\"rfEnabled\":false}");
  NimBLEDevice::getAdvertising()->addServiceUUID(SERVICE_UUID);
  NimBLEDevice::getAdvertising()->start();
  Serial.println("{\"type\":\"ble\",\"advertising\":true}");
}

void loop() {
  while (Serial.available()) {
    char ch = static_cast<char>(Serial.read());
    if (ch == '\n' || ch == '\r') {
      if (discardUntilNewline) {
        discardUntilNewline = false;
        commandBuffer = "";
        reportError("command_too_long", "Commands must be 256 bytes or fewer.");
      } else if (commandBuffer.length()) {
        dispatchCommand(commandBuffer);
        commandBuffer = "";
      }
    } else if (!discardUntilNewline) {
      if (commandBuffer.length() < MAX_COMMAND_BYTES) {
        commandBuffer += ch;
      } else {
        // Drop the entire oversized line instead of dispatching a truncated command.
        commandBuffer = "";
        discardUntilNewline = true;
      }
    }
  }
  // Receive -> validate/deduplicate -> route. The adapter remains inert unless
  // its verified board config and feature flags are enabled at compile time.
  ml::Packet incoming;
  if (radioLink.poll(incoming)) {
    ml::Packet forwarded;
    const ml::MeshAction action = meshRouter.process(incoming, localNodeId, millis(), forwarded);
    if (action == ml::MeshAction::ForwardOnly ||
        action == ml::MeshAction::DeliverAndForward) {
      radioLink.transmit(forwarded);
    }
    const ml::RadioStatus rs = radioLink.status();
    String event = "{\"type\":\"mesh\",\"action\":";
    event += String(static_cast<uint8_t>(action));
    event += ",\"source\":\"";
    event += ml::hexId(incoming.source, sizeof(incoming.source)).c_str();
    event += "\",\"rssi\":";
    event += String(rs.lastRssi);
    event += ",\"snr\":";
    event += String(rs.lastSnr);
    event += "}";
    report(event);
  }
  delay(5);
}
