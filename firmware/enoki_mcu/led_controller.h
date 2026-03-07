#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

class LedController {
 public:
  void begin();
  void setMood(int r, int g, int b, float brightness, const char* nudge_intensity);
  void setGroveLeds(const int* member_states, int count);
  void animateCelebrate();
  void update();

 private:
  int r_, g_, b_;
  float brightness_;
  unsigned long anim_start_;
  bool animating_;
};

#endif
