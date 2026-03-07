#ifndef MOTOR_CONTROLLER_H
#define MOTOR_CONTROLLER_H

#include <Arduino.h>

#define ENC_A_PIN   2
#define ENC_B_PIN   3
#define MOTOR_IN1   4
#define MOTOR_IN2   5
#define MOTOR_ENA   6

#define MAX_PULSES      400   // calibrate: full rack travel in encoder pulses
#define DEAD_ZONE       5     // pulses — stop motor when this close to target
#define HOMING_PWM      75    // ~30% of 255 for gentle homing
#define STALL_TIMEOUT   250   // ms with no encoder change = stalled (at bottom)

class MotorController {
 public:
  void begin();
  void setTarget(float height);
  void update();

  float getPosition() const;
  long  getEncoderRaw() const;
  bool  isHomed() const;
  const char* getMotorState() const;

 private:
  void home();
  void drive(int pwm);  // positive = up, negative = down, 0 = brake

  volatile long encoder_pos_;
  long target_pos_;
  long prev_error_;
  bool homed_;
  bool moving_;

  float kp_;
  float kd_;

  static MotorController* instance_;
  static void encoderISR_A();
};

#endif
