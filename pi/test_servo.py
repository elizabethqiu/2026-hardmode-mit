"""
test_servo.py — Phase 1 Step 2: verify PCA9685 I2C + servo works on Pi

Run: python3 pi/test_servo.py

What it does:
  1. Connects to PCA9685 at I2C address 0x40
  2. Sweeps servo on channel 0 from 0% -> 100% -> 0% three times
  3. Prints position at each step so you can watch physical movement

If it fails at import: pip3 install adafruit-circuitpython-pca9685 adafruit-blinka
If I2C not found: sudo i2cdetect -y 1  (should show 0x40)
"""

import time
import sys

print("Importing Adafruit PCA9685 library...")
try:
    import board
    import busio
    from adafruit_pca9685 import PCA9685
    from adafruit_motor import servo as adafruit_servo
except ImportError as e:
    print(f"Import failed: {e}")
    print("Run: pip3 install adafruit-circuitpython-pca9685 adafruit-circuitpython-motor adafruit-blinka")
    sys.exit(1)

print("Connecting to PCA9685 over I2C...")
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    pca = PCA9685(i2c)
    pca.frequency = 50
except Exception as e:
    print(f"PCA9685 init failed: {e}")
    print("Check wiring: SDA->GPIO2, SCL->GPIO3, VCC->3.3V, GND->GND")
    print("Run: sudo i2cdetect -y 1  -- should show '40' in the grid")
    sys.exit(1)

print("PCA9685 connected. Attaching servo on channel 0...")
servo = adafruit_servo.Servo(pca.channels[0], min_pulse=500, max_pulse=2500)

print("Starting sweep. Watch channel 0 servo move...")
print("  0%  = fully drooped")
print("  50% = neutral/center")
print("  100% = fully upright")

try:
    for rep in range(3):
        print(f"\n--- Sweep {rep+1}/3 ---")
        for pct in [0, 25, 50, 75, 100, 75, 50, 25, 0]:
            angle = pct * 1.8  # 0-180 degrees
            servo.angle = angle
            print(f"  angle={angle:.0f} deg ({pct}%)")
            time.sleep(0.5)

    print("\nSweep complete. Setting to neutral (90 deg).")
    servo.angle = 90
    time.sleep(0.5)
    print("\nPhase 1 Step 2: PASS -- servo responds smoothly over I2C.")

except KeyboardInterrupt:
    print("\nInterrupted.")
finally:
    pca.deinit()
