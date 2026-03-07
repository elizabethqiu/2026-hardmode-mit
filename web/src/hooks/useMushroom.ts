"use client";

import { useState, useCallback } from "react";

interface MushroomState {
  height: number;
  color: [number, number, number];
  brightness: number;
  mood: string;
  isBreathing: boolean;
  isCelebrating: boolean;
  groveLights: { color: [number, number, number]; brightness: number }[];
}

const MOOD_DEFAULTS: Record<string, Partial<MushroomState>> = {
  focused: { height: 0.95, color: [20, 200, 60], brightness: 1.0 },
  watchful: { height: 0.8, color: [200, 180, 120], brightness: 0.75 },
  concerned: { height: 0.55, color: [255, 140, 0], brightness: 0.6 },
  gentle: { height: 0.5, color: [220, 120, 0], brightness: 0.55 },
  urgent: { height: 0.3, color: [200, 30, 10], brightness: 0.5 },
};

function normalizeColor(value: unknown): [number, number, number] | null {
  if (
    Array.isArray(value) &&
    value.length === 3 &&
    value.every((v) => typeof v === "number")
  ) {
    return [value[0], value[1], value[2]];
  }
  return null;
}

export function useMushroom() {
  const [state, setState] = useState<MushroomState>({
    height: 0.7,
    color: [200, 180, 120],
    brightness: 0.75,
    mood: "watchful",
    isBreathing: false,
    isCelebrating: false,
    groveLights: [],
  });

  const applyClaudeResponse = useCallback((response: Record<string, unknown>) => {
    setState((prev) => ({
      ...prev,
      height: (response.height as number) ?? prev.height,
      color: normalizeColor(response.led_color) ?? prev.color,
      brightness: (response.led_brightness as number) ?? prev.brightness,
      mood: (response.enoki_mood as string) ?? prev.mood,
      isBreathing: response.nudge_intensity === "direct",
      isCelebrating: false,
    }));
  }, []);

  const applyMoodPreset = useCallback((mood: string) => {
    const preset = MOOD_DEFAULTS[mood];
    if (preset) {
      setState((prev) => ({ ...prev, ...preset, mood }));
    }
  }, []);

  const celebrate = useCallback(() => {
    setState((prev) => ({ ...prev, isCelebrating: true }));
    setTimeout(() => setState((prev) => ({ ...prev, isCelebrating: false })), 3500);
  }, []);

  const setGroveLights = useCallback(
    (lights: { color: [number, number, number]; brightness: number }[]) => {
      setState((prev) => ({ ...prev, groveLights: lights }));
    },
    []
  );

  return { ...state, applyClaudeResponse, applyMoodPreset, celebrate, setGroveLights };
}
