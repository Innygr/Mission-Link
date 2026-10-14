#include <unity.h>
#include <string.h>
#include <initializer_list>
#include "missionlink_display.h"

using Rows = char[ml::kDisplayRows][ml::kDisplayCols + 1];
static const ml::DisplayLayout kCompact = ml::DisplayLayout::Compact72x40;
static const ml::DisplayLayout kWide = ml::DisplayLayout::Wide128x64;

static ml::ConnectivitySnapshot base() {
  ml::ConnectivitySnapshot s{};
  s.firmware = "0.2.1"; s.bleAdvertising = true; s.radioState = "disabled"; s.preset = "client";
  return s;
}
static ml::ConnectivitySnapshot live() {
  auto s = base(); s.usbHostConnected = true; s.bleClients = 2; s.radioInitialized = true; s.radioReceiving = true;
  s.radioState = "ready"; s.hasSignal = true; s.packetsReceived = 12; s.lastRssi = -97; s.lastSnr = -3;
  return s;
}
static void render(const ml::ConnectivitySnapshot& s, ml::DisplayLayout layout, Rows rows) {
  memset(rows, 'X', sizeof(Rows));
  ml::formatStatusLines(s, layout, rows);
}

void test_geometry(){
  TEST_ASSERT_EQUAL(5, ml::displayGeometry(kCompact).rows); TEST_ASSERT_EQUAL(14, ml::displayGeometry(kCompact).cols);
  TEST_ASSERT_EQUAL(6, ml::displayGeometry(kWide).rows); TEST_ASSERT_EQUAL(21, ml::displayGeometry(kWide).cols);
}
void test_compact_idle(){
  Rows r; render(base(), kCompact, r);
  TEST_ASSERT_EQUAL_STRING("MissionLink", r[0]);
  TEST_ASSERT_EQUAL_STRING("USB- BLE adv", r[1]);
  TEST_ASSERT_EQUAL_STRING("LoRa off", r[2]);
  TEST_ASSERT_EQUAL_STRING("Rx 0", r[3]);
  TEST_ASSERT_EQUAL_STRING("TXoff client", r[4]);
  TEST_ASSERT_EQUAL_STRING("", r[5]);  // unused row is cleared
}
void test_compact_live(){
  Rows r; render(live(), kCompact, r);
  TEST_ASSERT_EQUAL_STRING("USB+ BLE 2", r[1]);
  TEST_ASSERT_EQUAL_STRING("LoRa RX on", r[2]);
  TEST_ASSERT_EQUAL_STRING("Rx12 -97dBm", r[3]);
}
void test_wide_idle(){
  Rows r; render(base(), kWide, r);
  TEST_ASSERT_EQUAL_STRING("MissionLink 0.2.1", r[0]);
  TEST_ASSERT_EQUAL_STRING("USB: no host", r[1]);
  TEST_ASSERT_EQUAL_STRING("BLE: advertising", r[2]);
  TEST_ASSERT_EQUAL_STRING("LoRa: off", r[3]);
  TEST_ASSERT_EQUAL_STRING("Rx 0 pkts", r[4]);
  TEST_ASSERT_EQUAL_STRING("TX off client", r[5]);
}
void test_wide_live(){
  Rows r; render(live(), kWide, r);
  TEST_ASSERT_EQUAL_STRING("USB: host connected", r[1]);
  TEST_ASSERT_EQUAL_STRING("BLE: 2 clients", r[2]);
  TEST_ASSERT_EQUAL_STRING("LoRa: RX listening", r[3]);
  TEST_ASSERT_EQUAL_STRING("Rx 12 -97dBm -3dB", r[4]);
}
void test_radio_state_labels(){
  auto s = base(); s.bleClients = 1; s.radioInitialized = true; s.radioState = "receive_error";
  Rows r; render(s, kWide, r);
  TEST_ASSERT_EQUAL_STRING("BLE: 1 client", r[2]);
  TEST_ASSERT_EQUAL_STRING("LoRa: RX error", r[3]);
  s.radioInitialized = false; s.radioState = "pinmap_unverified";
  render(s, kWide, r);
  TEST_ASSERT_EQUAL_STRING("LoRa: pins unverified", r[3]);
}
void test_rows_never_exceed_screen_width(){
  auto s = live(); s.firmware = "0.2.1-very-long-development-build"; s.radioInitialized = false; s.radioState = "pinmap_unverified";
  s.packetsReceived = 4294967295u; s.lastRssi = -32768; s.lastSnr = -128; s.preset = "repeater"; s.bleClients = 255;
  for (auto layout : {kCompact, kWide}) {
    Rows r; render(s, layout, r);
    const auto g = ml::displayGeometry(layout);
    for (size_t i = 0; i < ml::kDisplayRows; ++i) TEST_ASSERT_TRUE(strlen(r[i]) <= g.cols);
  }
}
void test_output_is_deterministic(){
  // StatusDisplay redraws only when the buffer changes, so identical input must give identical bytes.
  Rows a, b; memset(a, 1, sizeof(Rows)); memset(b, 2, sizeof(Rows));
  ml::formatStatusLines(live(), kCompact, a); ml::formatStatusLines(live(), kCompact, b);
  TEST_ASSERT_EQUAL_MEMORY(a, b, sizeof(Rows));
}
void test_null_strings_are_safe(){
  ml::ConnectivitySnapshot s{};
  Rows r; render(s, kWide, r);
  TEST_ASSERT_EQUAL_STRING("MissionLink ?", r[0]);
  TEST_ASSERT_EQUAL_STRING("LoRa: ?", r[3]);
  render(s, kCompact, r);
  TEST_ASSERT_EQUAL_STRING("LoRa ?", r[2]);
}
int main(int, char**){ UNITY_BEGIN();
  RUN_TEST(test_geometry); RUN_TEST(test_compact_idle); RUN_TEST(test_compact_live); RUN_TEST(test_wide_idle);
  RUN_TEST(test_wide_live); RUN_TEST(test_radio_state_labels); RUN_TEST(test_rows_never_exceed_screen_width);
  RUN_TEST(test_output_is_deterministic); RUN_TEST(test_null_strings_are_safe);
  return UNITY_END(); }
