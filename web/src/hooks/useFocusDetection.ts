"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FocusDetector } from "@/lib/focus/detector";
import { FocusStateMachine, type FocusState } from "@/lib/focus/state-machine";
import { createClient } from "@/lib/supabase/client";

const DETECT_INTERVAL = 200; // 5 FPS
const PUBLISH_INTERVAL = 30_000; // 30 seconds

export function useFocusDetection() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [state, setState] = useState<FocusState>("AWAY");
  const [duration, setDuration] = useState(0);
  const [isDetecting, setIsDetecting] = useState(false);
  const [ear, setEar] = useState(1);
  const detectorRef = useRef<FocusDetector | null>(null);
  const smRef = useRef(new FocusStateMachine());
  const sessionStartRef = useRef(Date.now());
  const focusSecondsRef = useRef(0);
  const publishTimerRef = useRef<ReturnType<typeof setInterval>>();
  const detectTimerRef = useRef<ReturnType<typeof setInterval>>();

  const startDetection = useCallback(async () => {
    if (isDetecting) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, facingMode: "user" },
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      const detector = new FocusDetector();
      await detector.init();
      detectorRef.current = detector;
      setIsDetecting(true);

      detectTimerRef.current = setInterval(() => {
        if (!videoRef.current || !detectorRef.current?.isReady) return;
        const result = detectorRef.current.detect(videoRef.current, performance.now());
        const dur = smRef.current.update(result.focusState);
        setState(result.focusState);
        setDuration(dur);
        setEar(result.eyeAspectRatio);

        if (result.focusState === "FOCUSED") {
          focusSecondsRef.current += DETECT_INTERVAL / 1000;
        }
      }, DETECT_INTERVAL);

      publishTimerRef.current = setInterval(() => {
        publishState();
      }, PUBLISH_INTERVAL);
    } catch (err) {
      console.error("Camera access failed:", err);
    }
  }, [isDetecting]);

  const stopDetection = useCallback(() => {
    if (detectTimerRef.current) clearInterval(detectTimerRef.current);
    if (publishTimerRef.current) clearInterval(publishTimerRef.current);
    if (videoRef.current?.srcObject) {
      (videoRef.current.srcObject as MediaStream).getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    detectorRef.current?.destroy();
    detectorRef.current = null;
    setIsDetecting(false);
    setState("AWAY");
  }, []);

  function publishState() {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return;
      const sessionMinutes = Math.round((Date.now() - sessionStartRef.current) / 60000);
      const todayFocusHours = Math.round((focusSecondsRef.current / 3600) * 10) / 10;
      supabase
        .from("focus_states")
        .upsert(
          {
            user_id: user.id,
            state: smRef.current.state,
            focus_score: ear,
            session_minutes: sessionMinutes,
            today_focus_hours: todayFocusHours,
            in_sprint: false,
            mushroom_mood: smRef.current.state === "FOCUSED" ? "focused" : "watchful",
            updated_at: new Date().toISOString(),
          },
          { onConflict: "user_id" }
        )
        .then();
    });
  }

  useEffect(() => {
    return () => stopDetection();
  }, [stopDetection]);

  const toggleDetection = useCallback(() => {
    if (isDetecting) stopDetection();
    else startDetection();
  }, [isDetecting, startDetection, stopDetection]);

  const sessionFocusPct = () => {
    const elapsed = Math.max((Date.now() - sessionStartRef.current) / 1000, 1);
    return Math.round((focusSecondsRef.current / elapsed) * 100);
  };

  return {
    state,
    duration,
    isDetecting,
    ear,
    videoRef,
    toggleDetection,
    startDetection,
    stopDetection,
    stateMachine: smRef.current,
    sessionFocusPct,
    focusSeconds: focusSecondsRef,
    sessionStart: sessionStartRef,
  };
}
