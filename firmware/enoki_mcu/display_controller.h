#ifndef DISPLAY_CONTROLLER_H
#define DISPLAY_CONTROLLER_H

#include <Arduino.h>

#define DISP_CS   10
#define DISP_DC    9
#define DISP_RST   8
#define DISP_BL    7

#define SCREEN_W  240
#define SCREEN_H  280

#define MAX_MSG_LEN   64
#define MAX_GROVE     12

class DisplayController {
 public:
  void begin();
  void showMood(const char* mood);
  void showMessage(const char* msg);
  void showState(const char* state, int focusMinutes);
  void showGroveStatus(const int colors[][3], int count);
  void setBacklight(uint8_t value);
  void clear();

 private:
  void drawFace(const char* mood, uint16_t color);
  void clearRegion(uint16_t y, uint16_t h, uint16_t color);
  uint16_t moodToColor(const char* mood);

  char current_mood_[16];
  char current_msg_[MAX_MSG_LEN];
};

#endif
