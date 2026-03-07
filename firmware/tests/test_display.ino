/**
 * test_display.ino — Standalone test for Seeed 1.69" IPS LCD (ST7789V2)
 *
 * Upload this sketch, open Serial Monitor at 115200.
 * The display will cycle through all 5 moods every 3 seconds.
 *
 * Serial commands:
 *   1 = focused
 *   2 = watchful
 *   3 = concerned
 *   4 = gentle
 *   5 = urgent
 */

#include "../enoki_mcu/display_controller.h"

DisplayController display;

static const char* MOODS[] = {"focused", "watchful", "concerned", "gentle", "urgent"};
static const char* MSGS[]  = {
  "Your gaze is steady. Strong session.",
  "I see you working. Keep it up.",
  "Your attention drifted a bit.",
  "Take a breath. You've been at it.",
  "You've been idle for 10 minutes."
};
static const int MOOD_COUNT = 5;

int currentMood = 0;
bool autoMode = true;
unsigned long lastSwitch = 0;

void setup() {
  Serial.begin(115200);
  Serial.println(F("=== Enoki Display Test ==="));

  display.begin();
  display.showMood(MOODS[0]);
  display.showMessage(MSGS[0]);
  display.showState("FOCUSED", 12);

  int grove[][3] = {{20,200,60}, {255,140,0}, {200,30,10}};
  display.showGroveStatus(grove, 3);

  Serial.println(F("Display initialized. Commands: 1-5 = mood, a = toggle auto"));
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c >= '1' && c <= '5') {
      autoMode = false;
      currentMood = c - '1';
      updateDisplay();
    } else if (c == 'a') {
      autoMode = !autoMode;
      Serial.print(F("Auto cycle: "));
      Serial.println(autoMode ? F("ON") : F("OFF"));
    }
  }

  if (autoMode && millis() - lastSwitch >= 3000) {
    lastSwitch = millis();
    currentMood = (currentMood + 1) % MOOD_COUNT;
    updateDisplay();
  }
}

void updateDisplay() {
  const char* mood = MOODS[currentMood];
  const char* msg  = MSGS[currentMood];

  Serial.print(F("Mood: "));
  Serial.print(mood);
  Serial.print(F("  Msg: "));
  Serial.println(msg);

  // Force redraw by clearing cached mood
  display.clear();
  display.showMood(mood);
  display.showMessage(msg);

  // Fake state based on mood
  const char* states[] = {"FOCUSED", "FOCUSED", "IDLE", "DOZING", "IDLE"};
  int minutes[] = {25, 12, 5, 2, 0};
  display.showState(states[currentMood], minutes[currentMood]);

  int grove[][3] = {{20,200,60}, {255,140,0}, {200,30,10}, {0,0,0}};
  display.showGroveStatus(grove, 4);
}
