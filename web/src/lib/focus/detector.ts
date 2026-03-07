import type { FocusState } from "./state-machine";

const EAR_THRESHOLD = 0.22;
const GAZE_THRESHOLD = 0.6;

const LEFT_EYE = [362, 385, 387, 263, 373, 380];
const RIGHT_EYE = [33, 160, 158, 133, 153, 144];

function dist(a: { x: number; y: number }, b: { x: number; y: number }) {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
}

function eyeAspectRatio(
  landmarks: { x: number; y: number }[],
  indices: number[]
): number {
  const [p1, p2, p3, p4, p5, p6] = indices.map((i) => landmarks[i]);
  const vertical1 = dist(p2, p6);
  const vertical2 = dist(p3, p5);
  const horizontal = dist(p1, p4);
  if (horizontal === 0) return 1;
  return (vertical1 + vertical2) / (2 * horizontal);
}

export interface DetectionResult {
  faceDetected: boolean;
  eyeAspectRatio: number;
  gazeScore: number;
  focusState: FocusState;
}

export class FocusDetector {
  private faceLandmarker: any = null;
  private ready = false;

  async init(): Promise<void> {
    const vision = await import("@mediapipe/tasks-vision");
    const { FaceLandmarker, FilesetResolver } = vision;

    const filesetResolver = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/wasm"
    );

    this.faceLandmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
      baseOptions: {
        modelAssetPath:
          "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        delegate: "GPU",
      },
      outputFaceBlendshapes: false,
      runningMode: "VIDEO",
      numFaces: 1,
    });

    this.ready = true;
  }

  get isReady() {
    return this.ready;
  }

  detect(video: HTMLVideoElement, timestamp: number): DetectionResult {
    if (!this.faceLandmarker || !this.ready) {
      return { faceDetected: false, eyeAspectRatio: 1, gazeScore: 1, focusState: "AWAY" };
    }

    const results = this.faceLandmarker.detectForVideo(video, timestamp);

    if (!results.faceLandmarks || results.faceLandmarks.length === 0) {
      return { faceDetected: false, eyeAspectRatio: 1, gazeScore: 0, focusState: "AWAY" };
    }

    const landmarks = results.faceLandmarks[0];
    const leftEar = eyeAspectRatio(landmarks, LEFT_EYE);
    const rightEar = eyeAspectRatio(landmarks, RIGHT_EYE);
    const avgEar = (leftEar + rightEar) / 2;

    const nose = landmarks[1];
    const gazeScore = 1 - Math.min(1, Math.abs(nose.x - 0.5) * 4);

    let focusState: FocusState;
    if (avgEar < EAR_THRESHOLD) {
      focusState = "DOZING";
    } else if (gazeScore < GAZE_THRESHOLD) {
      focusState = "IDLE";
    } else {
      focusState = "FOCUSED";
    }

    return { faceDetected: true, eyeAspectRatio: avgEar, gazeScore, focusState };
  }

  destroy() {
    if (this.faceLandmarker) {
      this.faceLandmarker.close();
      this.faceLandmarker = null;
      this.ready = false;
    }
  }
}
