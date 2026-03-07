/**
 * enoki_mcu.ino — Arduino UNO Q firmware for Enoki mushroom
 *
 * Reads JSON commands from serial (sent by laptop orchestrator).
 * Drives: JGA25-371 DC motor via L298N (rack & pinion lift),
 *         SK9822 LED strip via FastLED, ST7789V2 IPS LCD display.
 * Sends back state JSON at 1Hz.
 */

#include "motor_controller.h"
#include "led_controller.h"
#include "display_controller.h"
#include "command_parser.h"

#define SERIAL_BAUD      115200
#define STATE_INTERVAL   1000

MotorController  motor;
LedController    leds;
DisplayController display;
CommandParser    parser;

unsigned long lastStateSend = 0;

void setup() {
  Serial.begin(SERIAL_BAUD);

  // Motor homes on begin (drives down, zeros encoder)
  motor.begin();

  leds.begin();
  display.begin();

  // Boot state
  display.showMood("watchful");
  display.showState("BOOT", 0);
  display.showMessage("Enoki is waking up...");
  leds.setMood(200, 180, 120, 0.5, "none");
}

void loop() {
  // 1. Parse incoming serial commands
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    if (line.length() > 0) {
      Command cmd = parser.parse(line);
      if (cmd.valid) {
        motor.setTarget(cmd.height);

        leds.setMood(cmd.led_color[0], cmd.led_color[1], cmd.led_color[2],
                     cmd.led_brightness, cmd.nudge_intensity);

        if (strlen(cmd.animate) > 0 && strcmp(cmd.animate, "celebrate") == 0) {
          leds.animateCelebrate();
        }

        if (cmd.has_grove_leds) {
          leds.setGroveLeds(cmd.grove_leds, cmd.grove_count);
        }

        display.showMood(cmd.enoki_mood);

        if (strlen(cmd.message) > 0) {
          display.showMessage(cmd.message);
        }
      }
    }
  }

  // 2. Run motor PID (must run every iteration)
  motor.update();

  // 3. Run LED animations
  leds.update();

  // 4. Send state back at 1Hz
  unsigned long now = millis();
  if (now - lastStateSend >= STATE_INTERVAL) {
    lastStateSend = now;
    sendState();
  }
}

void sendState() {
  Serial.print(F("{\"height\":"));
  Serial.print(motor.getPosition(), 3);
  Serial.print(F(",\"encoder_pos\":"));
  Serial.print(motor.getEncoderRaw());
  Serial.print(F(",\"motor_state\":\""));
  Serial.print(motor.getMotorState());
  Serial.print(F("\",\"homed\":"));
  Serial.print(motor.isHomed() ? F("true") : F("false"));
  Serial.println(F("}"));
}
