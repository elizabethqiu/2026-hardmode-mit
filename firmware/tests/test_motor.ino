/**
 * test_motor.ino — Standalone test for JGA25-371 + L298N + encoder
 *
 * Upload this sketch, open Serial Monitor at 115200.
 * The motor will home (drive down until stall), then oscillate up/down.
 *
 * Serial commands:
 *   u  = go to 1.0 (full up)
 *   d  = go to 0.0 (full down)
 *   h  = re-home
 *   0-9 = set height to 0%-90% in 10% steps
 */

#include "../enoki_mcu/motor_controller.h"

MotorController motor;

unsigned long lastPrint = 0;
unsigned long lastToggle = 0;
bool goingUp = true;
bool autoMode = true;

void setup() {
  Serial.begin(115200);
  Serial.println(F("=== Enoki Motor Test ==="));
  Serial.println(F("Homing..."));

  motor.begin();

  Serial.print(F("Homed. Encoder zero: "));
  Serial.println(motor.getEncoderRaw());
  Serial.println(F("Auto-oscillate ON. Commands: u/d/h/0-9, a=toggle auto"));
}

void loop() {
  // Handle serial commands
  if (Serial.available()) {
    char c = Serial.read();
    switch (c) {
      case 'u':
        autoMode = false;
        motor.setTarget(1.0);
        Serial.println(F("-> Target: 1.0 (up)"));
        break;
      case 'd':
        autoMode = false;
        motor.setTarget(0.0);
        Serial.println(F("-> Target: 0.0 (down)"));
        break;
      case 'h':
        autoMode = false;
        Serial.println(F("Re-homing..."));
        motor.begin();
        Serial.println(F("Homed."));
        break;
      case 'a':
        autoMode = !autoMode;
        Serial.print(F("Auto-oscillate: "));
        Serial.println(autoMode ? F("ON") : F("OFF"));
        break;
      default:
        if (c >= '0' && c <= '9') {
          autoMode = false;
          float h = (c - '0') / 10.0f;
          motor.setTarget(h);
          Serial.print(F("-> Target: "));
          Serial.println(h, 2);
        }
        break;
    }
  }

  // Auto oscillate: up 3s, down 3s
  if (autoMode) {
    unsigned long now = millis();
    if (now - lastToggle >= 3000) {
      lastToggle = now;
      goingUp = !goingUp;
      motor.setTarget(goingUp ? 1.0f : 0.0f);
    }
  }

  // Run PID
  motor.update();

  // Print status every 100ms
  unsigned long now = millis();
  if (now - lastPrint >= 100) {
    lastPrint = now;
    Serial.print(F("pos="));
    Serial.print(motor.getPosition(), 3);
    Serial.print(F("  enc="));
    Serial.print(motor.getEncoderRaw());
    Serial.print(F("  state="));
    Serial.println(motor.getMotorState());
  }
}
