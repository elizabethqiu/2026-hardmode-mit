/**
 * HTTP client that POSTs sensor data to the orchestrator's glasses receiver
 * and polls for pending TTS to speak through the glasses.
 */

import type { GlassesPayload, TTSRequest } from "./types.js";

const DEFAULT_ORCHESTRATOR_URL = "http://localhost:8420";

export function getOrchestratorUrl(): string {
  return process.env.ORCHESTRATOR_URL ?? DEFAULT_ORCHESTRATOR_URL;
}

export async function postGlassesData(payload: GlassesPayload): Promise<void> {
  const url = `${getOrchestratorUrl()}/glasses`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, timestamp: Date.now() }),
  });
  if (!res.ok) {
    throw new Error(`Orchestrator POST failed: ${res.status}`);
  }
}

export async function getPendingTTS(): Promise<TTSRequest | null> {
  const url = `${getOrchestratorUrl()}/glasses/tts`;
  const res = await fetch(url);
  if (!res.ok || res.status === 204) return null;
  return (await res.json()) as TTSRequest;
}
