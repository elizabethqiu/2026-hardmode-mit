#ifndef COMMAND_PARSER_H
#define COMMAND_PARSER_H

#include <Arduino.h>

struct Command {
  bool valid;
  float stem_height;
  float cap_openness;
  int led_color[3];
  float led_brightness;
  String nudge_intensity;
  String animate;
};

class CommandParser {
 public:
  Command parse(const String& json);
};

#endif
