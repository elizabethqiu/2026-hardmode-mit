#include "command_parser.h"
#include <ArduinoJson.h>

Command CommandParser::parse(const String& json) {
  Command cmd;
  memset(&cmd, 0, sizeof(cmd));
  cmd.valid = false;
  cmd.height = 0.5f;
  cmd.led_color[0] = 200; cmd.led_color[1] = 180; cmd.led_color[2] = 120;
  cmd.led_brightness = 0.6f;
  strlcpy(cmd.nudge_intensity, "none", sizeof(cmd.nudge_intensity));
  strlcpy(cmd.enoki_mood, "watchful", sizeof(cmd.enoki_mood));
  cmd.message[0] = '\0';
  cmd.animate[0] = '\0';
  cmd.has_grove_leds = false;
  cmd.grove_count = 0;

  StaticJsonDocument<768> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) return cmd;

  cmd.valid = true;
  cmd.height = doc["height"] | 0.5f;
  cmd.led_brightness = doc["led_brightness"] | 0.6f;

  JsonArray color = doc["led_color"];
  if (color.size() >= 3) {
    cmd.led_color[0] = color[0] | 200;
    cmd.led_color[1] = color[1] | 180;
    cmd.led_color[2] = color[2] | 120;
  }

  const char* nudge = doc["nudge_intensity"];
  if (nudge) strlcpy(cmd.nudge_intensity, nudge, sizeof(cmd.nudge_intensity));

  const char* mood = doc["enoki_mood"];
  if (mood) strlcpy(cmd.enoki_mood, mood, sizeof(cmd.enoki_mood));

  const char* msg = doc["message"];
  if (msg) strlcpy(cmd.message, msg, sizeof(cmd.message));

  const char* anim = doc["animate"];
  if (anim) strlcpy(cmd.animate, anim, sizeof(cmd.animate));

  JsonArray grove = doc["grove_leds"];
  if (grove.size() > 0) {
    cmd.has_grove_leds = true;
    cmd.grove_count = min((int)grove.size(), CMD_MAX_GROVE);
    for (int i = 0; i < cmd.grove_count; i++) {
      JsonArray member = grove[i];
      if (member.size() >= 3) {
        cmd.grove_leds[i][0] = member[0] | 0;
        cmd.grove_leds[i][1] = member[1] | 0;
        cmd.grove_leds[i][2] = member[2] | 0;
      }
    }
  }

  return cmd;
}
