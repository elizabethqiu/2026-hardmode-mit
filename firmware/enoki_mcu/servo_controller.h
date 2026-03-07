#ifndef SERVO_CONTROLLER_H
#define SERVO_CONTROLLER_H

class ServoController {
 public:
  void begin();
  void setStemHeight(float value);   // 0.0-1.0
  void setCapOpenness(float value);   // 0.0-1.0

 private:
  float stem_height_;
  float cap_openness_;
  static const int STEM_SERVO_CHANNEL = 0;
  static const int CAP_SERVO_CHANNEL = 1;
};

#endif
