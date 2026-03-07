#include "led_controller.h"
#include <Adafruit_NeoPixel.h>

#define LED_PIN 6
#define LED_COUNT 12

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void LedController::begin() {
  strip.begin();
  strip.show();
  r_ = 200; g_ = 180; b_ = 120;
  brightness_ = 0.75f;
  animating_ = false;
}

void LedController::setMood(int r, int g, int b, float brightness, const char* nudge_intensity) {
  r_ = r; g_ = g; b_ = b;
  brightness_ = constrain(brightness, 0.0f, 1.0f);
  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, strip.Color(
      (int)(r_ * brightness_), (int)(g_ * brightness_), (int)(b_ * brightness_)));
  }
  strip.show();
}

void LedController::setGroveLeds(const int* member_states, int count) {
  for (int i = 0; i < min(count, LED_COUNT); i++) {
    int s = member_states[i];
    int r = (s == 1) ? 20 : (s == 0) ? 255 : 0;
    int g = (s == 1) ? 200 : (s == 0) ? 140 : 0;
    int b = (s == 1) ? 60 : (s == 0) ? 0 : 0;
    strip.setPixelColor(i, strip.Color(r, g, b));
  }
  strip.show();
}

void LedController::animateCelebrate() {
  anim_start_ = millis();
  animating_ = true;
}

void LedController::update() {
  if (!animating_) return;
  unsigned long elapsed = millis() - anim_start_;
  if (elapsed > 3000) { animating_ = false; return; }
  float t = (elapsed % 500) / 500.0f;
  float b = 0.5f + 0.5f * sin(t * 6.28f);
  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, strip.Color(
      (int)(r_ * b), (int)(g_ * b), (int)(b_ * b)));
  }
  strip.show();
}
