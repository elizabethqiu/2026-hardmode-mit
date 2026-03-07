/**
 * test_leds.ino — Standalone test for SK9822 LED strip via FastLED
 *
 * Upload this sketch, open Serial Monitor at 115200.
 * Auto-cycles through color modes every 3 seconds.
 *
 * Serial commands:
 *   1 = green (focused)
 *   2 = warm white (watchful)
 *   3 = amber (concerned)
 *   4 = red (urgent)
 *   c = celebrate animation
 *   b = breathe animation
 *   g = grove test (4 fake members)
 *   a = toggle auto cycle
 */

#include "../enoki_mcu/led_controller.h"

LedController leds;

unsigned long lastSwitch = 0;
int phase = 0;
bool autoMode = true;

void showPhase(int p);

void setup() {
  Serial.begin(115200);
  Serial.println(F("=== Enoki LED Test (SK9822) ==="));

  leds.begin();
  showPhase(0);

  Serial.println(F("Commands: 1-4=colors, c=celebrate, b=breathe, g=grove, a=auto"));
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    switch (c) {
      case '1':
        autoMode = false;
        leds.setMood(20, 200, 60, 1.0, "none");
        Serial.println(F("-> Green (focused)"));
        break;
      case '2':
        autoMode = false;
        leds.setMood(200, 180, 120, 0.75, "none");
        Serial.println(F("-> Warm white (watchful)"));
        break;
      case '3':
        autoMode = false;
        leds.setMood(255, 140, 0, 0.8, "none");
        Serial.println(F("-> Amber (concerned)"));
        break;
      case '4':
        autoMode = false;
        leds.setMood(200, 30, 10, 0.9, "none");
        Serial.println(F("-> Red (urgent)"));
        break;
      case 'c':
        autoMode = false;
        leds.animateCelebrate();
        Serial.println(F("-> Celebrate!"));
        break;
      case 'b':
        autoMode = false;
        leds.setMood(200, 30, 10, 0.8, "direct");
        Serial.println(F("-> Breathe (direct nudge)"));
        break;
      case 'g': {
        autoMode = false;
        int grove[][3] = {{20,200,60}, {255,140,0}, {200,30,10}, {20,200,60}};
        leds.setGroveLeds(grove, 4);
        Serial.println(F("-> Grove: 4 members"));
        break;
      }
      case 'a':
        autoMode = !autoMode;
        Serial.print(F("Auto: "));
        Serial.println(autoMode ? F("ON") : F("OFF"));
        break;
    }
  }

  if (autoMode && millis() - lastSwitch >= 3000) {
    lastSwitch = millis();
    phase = (phase + 1) % 6;
    showPhase(phase);
  }

  leds.update();
  delay(10);
}

void showPhase(int p) {
  switch (p) {
    case 0:
      leds.setMood(20, 200, 60, 1.0, "none");
      Serial.println(F("[auto] Green"));
      break;
    case 1:
      leds.setMood(255, 140, 0, 0.8, "none");
      Serial.println(F("[auto] Amber"));
      break;
    case 2:
      leds.setMood(200, 30, 10, 0.9, "none");
      Serial.println(F("[auto] Red"));
      break;
    case 3:
      leds.animateCelebrate();
      Serial.println(F("[auto] Celebrate"));
      break;
    case 4: {
      int grove[][3] = {{20,200,60}, {255,140,0}, {200,30,10}, {0,0,0}};
      leds.setGroveLeds(grove, 4);
      Serial.println(F("[auto] Grove"));
      break;
    }
    case 5:
      leds.setMood(200, 30, 10, 0.8, "direct");
      Serial.println(F("[auto] Breathe"));
      break;
  }
}
