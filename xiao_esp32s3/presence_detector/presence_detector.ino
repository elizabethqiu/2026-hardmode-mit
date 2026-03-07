/*
 * presence_detector.ino — Seeed XIAO ESP32-S3 Sense
 *
 * Uses ESP-WHO face detection (built on ESP-IDF + TFLite) to detect
 * face presence and approximate eye state via face bounding-box aspect ratio.
 *
 * Output JSON over USB Serial at ~10Hz:
 *   {"face":true,"eyes_open":true,"confidence":0.87}
 *
 * Board: Seeed XIAO ESP32-S3 Sense
 * Framework: Arduino (ESP32 Arduino core)
 * Camera: OV2640 via onboard DVP connector
 *
 * Library dependencies:
 *   - ESP32 Arduino core (espressif/arduino-esp32)
 *   - esp-who (Espressif ESP-WHO, included in ESP-IDF component registry)
 *     OR use the standalone face_detection example from ESP-WHO repo
 *
 * Note: In ESP-WHO's Arduino wrapper, face detection is exposed via
 *   HumanFaceDetect class from esp_face_detect.hpp
 */

#include <Arduino.h>
#include "esp_camera.h"
#include "esp_face_detect.hpp"  // from ESP-WHO component

// ── Camera pin config for XIAO ESP32-S3 Sense OV2640 ─────────────────────
#define PWDN_GPIO_NUM   -1
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM   10
#define SIOD_GPIO_NUM   40
#define SIOC_GPIO_NUM   39
#define Y9_GPIO_NUM     48
#define Y8_GPIO_NUM     11
#define Y7_GPIO_NUM     12
#define Y6_GPIO_NUM     14
#define Y5_GPIO_NUM     16
#define Y4_GPIO_NUM     18
#define Y3_GPIO_NUM     17
#define Y2_GPIO_NUM     15
#define VSYNC_GPIO_NUM  38
#define HREF_GPIO_NUM   47
#define PCLK_GPIO_NUM   13

// ── Eye-open heuristic ─────────────────────────────────────────────────────
// ESP-WHO returns face bounding box. Eyes are roughly in the top 40% of box.
// We use aspect ratio change as a coarse proxy: very wide/short box → drooping.
// Fine-grained eye tracking requires MediaPipe (on Pi) — this is presence only.
#define EYE_ASPECT_THRESHOLD 0.45f   // box h/w below this → likely drooping

// ── Face detector ──────────────────────────────────────────────────────────
HumanFaceDetect* detector = nullptr;

camera_config_t cameraConfig() {
  camera_config_t cfg;
  cfg.pin_pwdn     = PWDN_GPIO_NUM;
  cfg.pin_reset    = RESET_GPIO_NUM;
  cfg.pin_xclk     = XCLK_GPIO_NUM;
  cfg.pin_sccb_sda = SIOD_GPIO_NUM;
  cfg.pin_sccb_scl = SIOC_GPIO_NUM;
  cfg.pin_d7       = Y9_GPIO_NUM;
  cfg.pin_d6       = Y8_GPIO_NUM;
  cfg.pin_d5       = Y7_GPIO_NUM;
  cfg.pin_d4       = Y6_GPIO_NUM;
  cfg.pin_d3       = Y5_GPIO_NUM;
  cfg.pin_d2       = Y4_GPIO_NUM;
  cfg.pin_d1       = Y3_GPIO_NUM;
  cfg.pin_d0       = Y2_GPIO_NUM;
  cfg.pin_vsync    = VSYNC_GPIO_NUM;
  cfg.pin_href     = HREF_GPIO_NUM;
  cfg.pin_pclk     = PCLK_GPIO_NUM;
  cfg.xclk_freq_hz = 20000000;
  cfg.ledc_timer   = LEDC_TIMER_0;
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.pixel_format = PIXFORMAT_RGB565;
  cfg.frame_size   = FRAMESIZE_QVGA;   // 320x240 — good for face detection
  cfg.fb_count     = 2;
  cfg.grab_mode    = CAMERA_GRAB_LATEST;
  return cfg;
}

void setup() {
  Serial.begin(115200);
  delay(500);

  camera_config_t cfg = cameraConfig();
  esp_err_t err = esp_camera_init(&cfg);
  if (err != ESP_OK) {
    Serial.printf("{\"error\":\"camera_init_failed:0x%x\"}\n", err);
    while (1) delay(1000);
  }

  // Two-stage: S1 = MobileNet SSD for face, S2 = landmark refinement
  detector = new HumanFaceDetect(0.5f, 0.3f, 10, 0.3f);

  Serial.println("{\"status\":\"presence_detector_ready\"}");
}

void loop() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("{\"error\":\"frame_capture_failed\"}");
    delay(50);
    return;
  }

  // Run face detection
  std::list<dl::detect::result_t> results =
    detector->infer((uint16_t*)fb->buf, {(int)fb->height, (int)fb->width, 3});

  bool faceDetected = !results.empty();
  bool eyesOpen     = true;
  float confidence  = 0.0f;

  if (faceDetected) {
    auto& best = results.front();
    confidence = best.score;

    // Coarse eye-open check via bounding box aspect ratio
    int x = best.box[0];
    int y = best.box[1];
    int w = best.box[2] - x;
    int h = best.box[3] - y;

    if (w > 0) {
      float ratio = (float)h / (float)w;
      eyesOpen = (ratio > EYE_ASPECT_THRESHOLD);
    }
  }

  esp_camera_fb_return(fb);

  // Output JSON
  Serial.printf(
    "{\"face\":%s,\"eyes_open\":%s,\"confidence\":%.2f}\n",
    faceDetected ? "true" : "false",
    eyesOpen     ? "true" : "false",
    confidence
  );

  delay(100);  // ~10Hz
}
