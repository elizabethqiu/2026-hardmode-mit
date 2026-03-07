/**
 * enoki_mcu.ino — Arduino UNO Q MCU sketch for Enoki mushroom
 *
 * Reads JSON commands from serial, drives PCA9685 servos and NeoPixel LEDs.
 * Sends back sensor state JSON at 1Hz.
 */

#include "servo_controller.h"
#include "led_controller.h"
#include "command_parser.h"

#define SERIAL_BAUD 115200
#define STATE_INTERVAL_MS 1000

ServoController servos;
LedController leds;
CommandParser parser;

unsigned long lastStateSend = 0;

void setup() {
  Serial.begin(SERIAL_BAUD);
  servos.begin();
  leds.begin();
}

void loop() {
  // Read incoming JSON commands
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    if (line.length() > 0) {
      Command cmd = parser.parse(line);
      if (cmd.valid) {
        servos.setStemHeight(cmd.stem_height);
        servos.setCapOpenness(cmd.cap_openness);
        leds.setMood(cmd.led_color, cmd.led_brightness, cmd.nudge_intensity);
        if (cmd.animate == "celebrate") {
          leds.animateCelebrate();
        }
      }
    }
  }

  // Send state back at 1Hz
  unsigned long now = millis();
  if (now - lastStateSend >= STATE_INTERVAL_MS) {
    lastStateSend = now;
    sendState();
  }

  leds.update();
  delay(10);
}

void sendState() {
  // Placeholder: Arduino would fuse sensor data here
  // For now send minimal state; XIAO provides face/eye data separately
  Serial.println("{\"state\":\"AWAY\",\"confidence\":0.0,\"sensors\":{}}");
}
