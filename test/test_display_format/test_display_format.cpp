#include <unity.h>
#include <string.h>
#include "missionlink_display.h"

static ml::ConnectivitySnapshot base() {
  ml::ConnectivitySnapshot s{};
  s.firmware = "0.2.1"; s.bleAdvertising = true; s.radioState = "disabled"; s.preset = "client";
  return s;
}
static void render(const ml::ConnectivitySnapshot& s, char rows[ml::kDisplayRows][ml::kDisplayCols + 1]) {
  memset(rows, 'X', ml::kDisplayRows * (ml::kDisplayCols + 1));
  ml::formatStatusLines(s, rows);
}

void test_idle_board(){
  char r[ml::kDisplayRows][ml::kDisplayCols + 1]; render(base(), r);
  TEST_ASSERT_EQUAL_STRING("MissionLink 0.2.1", r[0]);
  TEST_ASSERT_EQUAL_STRING("USB: no host", r[1]);
  TEST_ASSERT_EQUAL_STRING("BLE: advertising", r[2]);
  TEST_ASSERT_EQUAL_STRING("LoRa: off", r[3]);
  TEST_ASSERT_EQUAL_STRING("Rx 0 pkts", r[4]);
  TEST_ASSERT_EQUAL_STRING("TX off client", r[5]);
}
void test_connected_and_receiving(){
  auto s = base(); s.usbHostConnected = true; s.bleClients = 2; s.radioInitialized = true; s.radioReceiving = true;
  s.radioState = "ready"; s.hasSignal = true; s.packetsReceived = 12; s.lastRssi = -97; s.lastSnr = -3;
  char r[ml::kDisplayRows][ml::kDisplayCols + 1]; render(s, r);
  TEST_ASSERT_EQUAL_STRING("USB: host connected", r[1]);
  TEST_ASSERT_EQUAL_STRING("BLE: 2 clients", r[2]);
  TEST_ASSERT_EQUAL_STRING("LoRa: RX listening", r[3]);
  TEST_ASSERT_EQUAL_STRING("Rx 12 -97dBm -3dB", r[4]);
}
void test_single_client_and_radio_error(){
  auto s = base(); s.bleClients = 1; s.radioInitialized = true; s.radioReceiving = false; s.radioState = "receive_error";
  char r[ml::kDisplayRows][ml::kDisplayCols + 1]; render(s, r);
  TEST_ASSERT_EQUAL_STRING("BLE: 1 client", r[2]);
  TEST_ASSERT_EQUAL_STRING("LoRa: RX error", r[3]);
}
void test_unverified_pinmap_fits(){
  auto s = base(); s.radioState = "pinmap_unverified";
  char r[ml::kDisplayRows][ml::kDisplayCols + 1]; render(s, r);
  TEST_ASSERT_EQUAL_STRING("LoRa: pins unverified", r[3]);
}
void test_rows_never_exceed_screen_width(){
  auto s = base(); s.firmware = "0.2.1-very-long-development-build"; s.radioState = "pinmap_unverified";
  s.hasSignal = true; s.packetsReceived = 4294967295u; s.lastRssi = -32768; s.lastSnr = -128; s.preset = "repeater";
  char r[ml::kDisplayRows][ml::kDisplayCols + 1]; render(s, r);
  for (size_t i = 0; i < ml::kDisplayRows; ++i) TEST_ASSERT_TRUE(strlen(r[i]) <= ml::kDisplayCols);
}
void test_null_strings_are_safe(){
  ml::ConnectivitySnapshot s{};
  char r[ml::kDisplayRows][ml::kDisplayCols + 1]; render(s, r);
  TEST_ASSERT_EQUAL_STRING("MissionLink ?", r[0]);
  TEST_ASSERT_EQUAL_STRING("LoRa: ?", r[3]);
}
int main(int, char**){ UNITY_BEGIN();
  RUN_TEST(test_idle_board); RUN_TEST(test_connected_and_receiving); RUN_TEST(test_single_client_and_radio_error);
  RUN_TEST(test_unverified_pinmap_fits); RUN_TEST(test_rows_never_exceed_screen_width); RUN_TEST(test_null_strings_are_safe);
  return UNITY_END(); }
