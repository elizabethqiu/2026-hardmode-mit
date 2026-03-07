#include "servo_controller.h"
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

void ServoController::begin() {
  pwm.begin();
  pwm.setPWMFreq(50);
  stem_height_ = 0.5f;
  cap_openness_ = 0.5f;
}

void ServoController::setStemHeight(float value) {
  stem_height_ = constrain(value, 0.0f, 1.0f);
  int pulse = 150 + (int)(stem_height_ * 400);  // 150-550 us typical range
  pwm.setPWM(STEM_SERVO_CHANNEL, 0, pulse);
}

void ServoController::setCapOpenness(float value) {
  cap_openness_ = constrain(value, 0.0f, 1.0f);
  int pulse = 150 + (int)(cap_openness_ * 400);
  pwm.setPWM(CAP_SERVO_CHANNEL, 0, pulse);
}
