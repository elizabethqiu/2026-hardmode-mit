#include "motor_controller.h"

MotorController* MotorController::instance_ = nullptr;

void MotorController::encoderISR_A() {
  if (!instance_) return;
  // Quadrature: read B to determine direction
  if (digitalRead(ENC_B_PIN) == HIGH) {
    instance_->encoder_pos_++;
  } else {
    instance_->encoder_pos_--;
  }
}

void MotorController::begin() {
  instance_ = this;

  pinMode(ENC_A_PIN, INPUT_PULLUP);
  pinMode(ENC_B_PIN, INPUT_PULLUP);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);

  encoder_pos_ = 0;
  target_pos_ = 0;
  prev_error_ = 0;
  homed_ = false;
  moving_ = false;

  kp_ = 2.0f;
  kd_ = 0.5f;

  attachInterrupt(digitalPinToInterrupt(ENC_A_PIN), encoderISR_A, RISING);

  home();
}

void MotorController::home() {
  homed_ = false;
  long last_pos = encoder_pos_;
  unsigned long last_change = millis();

  // Drive down gently until stall detected
  drive(-HOMING_PWM);

  while (true) {
    long pos = encoder_pos_;
    if (pos != last_pos) {
      last_pos = pos;
      last_change = millis();
    }
    if (millis() - last_change >= STALL_TIMEOUT) {
      break;  // encoder hasn't moved — we hit bottom
    }
    delay(5);
  }

  drive(0);
  encoder_pos_ = 0;
  target_pos_ = 0;
  prev_error_ = 0;
  homed_ = true;
}

void MotorController::setTarget(float height) {
  height = constrain(height, 0.0f, 1.0f);
  target_pos_ = (long)(height * MAX_PULSES);
}

void MotorController::update() {
  if (!homed_) return;

  long current = encoder_pos_;
  long error = target_pos_ - current;

  if (abs(error) <= DEAD_ZONE) {
    if (moving_) {
      drive(0);
      moving_ = false;
    }
    prev_error_ = 0;
    return;
  }

  long derivative = error - prev_error_;
  float output = kp_ * error + kd_ * derivative;
  prev_error_ = error;

  int pwm = constrain((int)output, -255, 255);

  // Minimum PWM to overcome static friction
  if (pwm > 0 && pwm < 40) pwm = 40;
  if (pwm < 0 && pwm > -40) pwm = -40;

  drive(pwm);
  moving_ = true;
}

void MotorController::drive(int pwm) {
  if (pwm > 0) {
    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, pwm);
  } else if (pwm < 0) {
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);
    analogWrite(MOTOR_ENA, -pwm);
  } else {
    // Brake: both LOW
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, 0);
  }
}

float MotorController::getPosition() const {
  return constrain((float)encoder_pos_ / MAX_PULSES, 0.0f, 1.0f);
}

long MotorController::getEncoderRaw() const {
  return encoder_pos_;
}

bool MotorController::isHomed() const {
  return homed_;
}

const char* MotorController::getMotorState() const {
  if (!homed_) return "homing";
  if (moving_) return "moving";
  return "holding";
}
