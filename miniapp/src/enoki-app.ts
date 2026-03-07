/**
 * Enoki MentraOS MiniApp — bridges glasses (camera, mic, speakers) to the orchestrator.
 * Subscribes to transcription and button events, captures photos periodically,
 * POSTs data to orchestrator, and speaks TTS responses from orchestrator.
 *
 * Wake phrase: only transcriptions starting with "enoki" or "hey enoki" are forwarded.
 */

import { AppServer } from "@mentraos/sdk";
import { postGlassesData, getPendingTTS, getPendingAction } from "./bridge.js";

const PHOTO_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
const WAKE_PHRASES = ["enoki", "hey enoki"];

function stripWakePhrase(text: string): string | null {
  const lower = text.toLowerCase().trim();
  for (const phrase of WAKE_PHRASES) {
    if (lower.startsWith(phrase)) {
      const rest = text.slice(phrase.length).replace(/^[,\s]+/, "").trim();
      return rest || null;
    }
  }
  return null;
}

export class EnokiApp extends AppServer {
  private photoTimer: ReturnType<typeof setInterval> | null = null;

  protected async onSession(session: any, sessionId: string, userId: string): Promise<void> {
    // Subscribe to transcription (voice input) — wake phrase filtered
    session.events.onTranscription?.((data: { text: string }) => {
      if (!data?.text?.trim()) return;
      const cleaned = stripWakePhrase(data.text.trim());
      if (cleaned) {
        postGlassesData({ transcription: cleaned, wearing: true }).catch(console.error);
      }
    });

    // Subscribe to button press (manual trigger)
    session.events.onButtonPress?.((data: { button: string }) => {
      if (data?.button === "MAIN") {
        postGlassesData({ button_pressed: true, wearing: true }).catch(console.error);
      }
    });

    // Periodic photo capture
    if (session.camera?.requestPhoto) {
      this.photoTimer = setInterval(async () => {
        try {
          const photo = await session.camera.requestPhoto({ size: "small" });
          if (photo?.buffer) {
            const base64 = Buffer.from(photo.buffer).toString("base64");
            await postGlassesData({ photo_base64: base64, wearing: true });
          }
        } catch (e) {
          console.warn("Photo capture failed:", e);
        }
      }, PHOTO_INTERVAL_MS);
    }

    // Poll for TTS and speak
    const ttsPollInterval = setInterval(async () => {
      try {
        const tts = await getPendingTTS();
        if (tts?.text && session.audio?.speak) {
          await session.audio.speak(tts.text);
        }
      } catch {
        // Orchestrator may be offline
      }
    }, 500);

    // Poll for action requests (e.g. photo capture on state change)
    const actionPollInterval = setInterval(async () => {
      try {
        const action = await getPendingAction();
        if (action?.action === "take_photo" && session.camera?.requestPhoto) {
          const photo = await session.camera.requestPhoto({ size: "small" });
          if (photo?.buffer) {
            const base64 = Buffer.from(photo.buffer).toString("base64");
            await postGlassesData({ photo_base64: base64, wearing: true });
          }
        }
      } catch {
        // Orchestrator may be offline
      }
    }, 2000);

    session.events.onDisconnect?.(() => {
      if (this.photoTimer) clearInterval(this.photoTimer);
      clearInterval(ttsPollInterval);
      clearInterval(actionPollInterval);
    });
  }
}
