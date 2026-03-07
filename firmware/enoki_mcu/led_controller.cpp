#include "led_controller.h"
#include <FastLED.h>

static CRGB leds[NUM_LEDS];

void LedController::begin() {
  FastLED.addLeds<APA102, LED_DATA_PIN, LED_CLOCK_PIN, BGR>(leds, NUM_LEDS);
  FastLED.setBrightness(190);
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();

  base_r_ = 200; base_g_ = 180; base_b_ = 120;
  brightness_ = 0.75f;
  animating_ = false;
  breathing_ = false;
  sprint_pulse_ = false;
  dirty_ = false;
}

void LedController::setMood(int r, int g, int b, float brightness, const char* nudge_intensity) {
  base_r_ = r;
  base_g_ = g;
  base_b_ = b;
  brightness_ = constrain(brightness, 0.0f, 1.0f);

  FastLED.setBrightness((uint8_t)(brightness_ * 255));

  fill_solid(leds, NUM_LEDS, CRGB(r, g, b));
  dirty_ = true;

  // "direct" nudge triggers a breathe effect
  breathing_ = (nudge_intensity && strcmp(nudge_intensity, "direct") == 0);
  if (breathing_) {
    anim_start_ = millis();
    animating_ = false;  // breathe overrides celebrate
  }
}

void LedController::setGroveLeds(const int colors[][3], int count) {
  int n = min(count, (int)NUM_LEDS);
  for (int i = 0; i < n; i++) {
    leds[i] = CRGB(colors[i][0], colors[i][1], colors[i][2]);
  }
  // Fill remaining LEDs with base mood color
  for (int i = n; i < NUM_LEDS; i++) {
    leds[i] = CRGB(base_r_, base_g_, base_b_);
  }
  dirty_ = true;
}

void LedController::animateCelebrate() {
  anim_start_ = millis();
  animating_ = true;
  breathing_ = false;
  sprint_pulse_ = false;
}

void LedController::setSprintPulse(bool active) {
  sprint_pulse_ = active;
  if (!active) {
    FastLED.setBrightness((uint8_t)(brightness_ * 255));
    dirty_ = true;
  }
}

void LedController::update() {
  if (animating_) {
    unsigned long elapsed = millis() - anim_start_;
    if (elapsed > 3000) {
      animating_ = false;
      // Restore base color
      fill_solid(leds, NUM_LEDS, CRGB(base_r_, base_g_, base_b_));
      dirty_ = true;
    } else {
      // Rainbow chase
      uint8_t hue_base = (elapsed / 10) & 0xFF;
      for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CHSV(hue_base + i * (256 / NUM_LEDS), 255, 255);
      }
      dirty_ = true;
    }
  }
  else if (breathing_) {
    unsigned long elapsed = millis() - anim_start_;
    if (elapsed > 10000) {
      breathing_ = false;
      FastLED.setBrightness((uint8_t)(brightness_ * 255));
      dirty_ = true;
    } else {
      uint8_t val = beatsin8(30, 40, 255);  // 30 BPM, range 40-255
      FastLED.setBrightness(val);
      dirty_ = true;
    }
  }
  else if (sprint_pulse_) {
    // Slow green pulse: 15 BPM, subtle brightness range
    uint8_t val = beatsin8(15, (uint8_t)(brightness_ * 120), (uint8_t)(brightness_ * 255));
    FastLED.setBrightness(val);
    fill_solid(leds, NUM_LEDS, CRGB(20, 200, 60));
    dirty_ = true;
  }

  if (dirty_) {
    FastLED.show();
    dirty_ = false;
  }
}
