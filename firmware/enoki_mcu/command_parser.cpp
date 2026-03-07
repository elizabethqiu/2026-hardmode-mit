#include "command_parser.h"
#include <ArduinoJson.h>

Command CommandParser::parse(const String& json) {
  Command cmd = {false, 0.5f, 0.5f, {200, 180, 120}, 0.6f, "none", ""};

  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) return cmd;

  cmd.valid = true;
  cmd.stem_height = doc["stem_height"] | 0.7f;
  cmd.cap_openness = doc["cap_openness"] | 0.5f;
  cmd.led_brightness = doc["led_brightness"] | 0.6f;
  cmd.nudge_intensity = doc["nudge_intensity"].as<String>() | "none";
  cmd.animate = doc["animate"].as<String>() | "";

  JsonArray arr = doc["led_color"];
  if (arr.size() >= 3) {
    cmd.led_color[0] = arr[0] | 200;
    cmd.led_color[1] = arr[1] | 180;
    cmd.led_color[2] = arr[2] | 120;
  }

  return cmd;
}
