"""
webcam.py — MediaPipe face mesh + eye/gaze tracking.

Refactored from pi/vision.py. Fixes unreachable cap.release() with try/finally.
Streams dicts: face_detected, eye_aspect_ratio, gaze_score.
"""

import logging
import time

import cv2
import numpy as np

log = logging.getLogger("enoki.sensors.webcam")

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
LEFT_IRIS_IDX = [474, 475, 476, 477]
RIGHT_IRIS_IDX = [469, 470, 471, 472]


def _eye_aspect_ratio(landmarks, indices, image_w, image_h):
    pts = np.array([[landmarks[i].x * image_w, landmarks[i].y * image_h] for i in indices])
    v1 = np.linalg.norm(pts[1] - pts[5])
    v2 = np.linalg.norm(pts[2] - pts[4])
    h = np.linalg.norm(pts[0] - pts[3])
    if h < 1e-6:
        return 0.0
    return (v1 + v2) / (2.0 * h)


def _gaze_score(landmarks, left_iris, right_iris, image_w, image_h):
    def iris_offset(eye_idx, iris_idx):
        eye_pts = np.array([[landmarks[i].x, landmarks[i].y] for i in eye_idx])
        iris_pts = np.array([[landmarks[i].x, landmarks[i].y] for i in iris_idx])
        eye_center = eye_pts.mean(axis=0)
        iris_center = iris_pts.mean(axis=0)
        eye_width = np.linalg.norm(eye_pts[0] - eye_pts[3])
        if eye_width < 1e-6:
            return 0.0
        return np.linalg.norm(iris_center - eye_center) / eye_width

    offset = (iris_offset(LEFT_EYE_IDX, left_iris) + iris_offset(RIGHT_EYE_IDX, right_iris)) / 2.0
    return max(0.0, 1.0 - offset * 4.0)


class VisionProcessor:
    """MediaPipe face mesh + iris tracking. Yields ~10fps results."""

    def __init__(
        self,
        camera_index: int = 0,
        fps_target: int = 10,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        self._camera_index = camera_index
        self._fps_target = fps_target
        self._min_detection = min_detection_confidence
        self._min_tracking = min_tracking_confidence

    def stream(self):
        """Generator that yields vision result dicts indefinitely."""
        try:
            import mediapipe as mp
        except ImportError:
            log.error("mediapipe not installed — vision disabled")
            yield from self._null_stream()
            return

        mp_face_mesh = mp.solutions.face_mesh
        cap = cv2.VideoCapture(self._camera_index)
        cap.set(cv2.CAP_PROP_FPS, self._fps_target)

        if not cap.isOpened():
            log.error("Could not open camera %d — vision disabled", self._camera_index)
            yield from self._null_stream()
            return

        try:
            with mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=self._min_detection,
                min_tracking_confidence=self._min_tracking,
            ) as face_mesh:
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        log.warning("Camera frame read failed")
                        yield self._empty()
                        continue

                    h, w = frame.shape[:2]
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    result = face_mesh.process(rgb)

                    if not result.multi_face_landmarks:
                        yield self._empty()
                        continue

                    lm = result.multi_face_landmarks[0].landmark
                    left_ear = _eye_aspect_ratio(lm, LEFT_EYE_IDX, w, h)
                    right_ear = _eye_aspect_ratio(lm, RIGHT_EYE_IDX, w, h)
                    ear = (left_ear + right_ear) / 2.0

                    try:
                        gaze = _gaze_score(lm, LEFT_IRIS_IDX, RIGHT_IRIS_IDX, w, h)
                    except Exception:
                        gaze = 1.0

                    yield {
                        "face_detected": True,
                        "eye_aspect_ratio": round(ear, 3),
                        "gaze_score": round(gaze, 3),
                    }
        finally:
            cap.release()

    @staticmethod
    def _empty():
        return {"face_detected": False, "eye_aspect_ratio": 0.0, "gaze_score": 0.0}

    @staticmethod
    def _null_stream():
        while True:
            time.sleep(0.1)
            yield VisionProcessor._empty()
