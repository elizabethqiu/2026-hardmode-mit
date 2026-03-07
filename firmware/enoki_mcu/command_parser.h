#ifndef COMMAND_PARSER_H
#define COMMAND_PARSER_H

#include <Arduino.h>

#define CMD_MSG_LEN    64
#define CMD_MOOD_LEN   16
#define CMD_MAX_GROVE  12

struct Command {
  bool valid;
  float height;
  int led_color[3];
  float led_brightness;
  char nudge_intensity[12];
  char enoki_mood[CMD_MOOD_LEN];
  char message[CMD_MSG_LEN];
  char animate[16];
  bool sprint_pulse;

  bool has_grove_leds;
  int grove_leds[CMD_MAX_GROVE][3];
  int grove_count;
};

class CommandParser {
 public:
  Command parse(const String& json);
};

#endif
