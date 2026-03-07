#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <Arduino.h>

#define LED_DATA_PIN   A3
#define LED_CLOCK_PIN  A4
#define NUM_LEDS       12
#define MAX_GROVE_LEDS 12

class LedController {
 public:
  void begin();
  void setMood(int r, int g, int b, float brightness, const char* nudge_intensity);
  void setGroveLeds(const int colors[][3], int count);
  void animateCelebrate();
  void update();

 private:
  int base_r_, base_g_, base_b_;
  float brightness_;
  bool animating_;
  bool breathing_;
  unsigned long anim_start_;
  bool dirty_;
};

#endif
