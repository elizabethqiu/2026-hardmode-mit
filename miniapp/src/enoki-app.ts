/**
 * Enoki MentraOS MiniApp — bridges glasses (camera, mic, speakers) to the orchestrator.
 * Subscribes to transcription and button events, captures photos periodically,
 * POSTs data to orchestrator, and speaks TTS responses from orchestrator.
 */

import { AppServer } from "@mentraos/sdk";
import { postGlassesData, getPendingTTS } from "./bridge.js";

const PHOTO_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export class EnokiApp extends AppServer {
  private photoTimer: ReturnType<typeof setInterval> | null = null;

  protected async onSession(session: any, sessionId: string, userId: string): Promise<void> {
    // Subscribe to transcription (voice input)
    session.events.onTranscription?.((data: { text: string }) => {
      if (data?.text?.trim()) {
        postGlassesData({ transcription: data.text.trim(), wearing: true }).catch(console.error);
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

    session.events.onDisconnect?.(() => {
      if (this.photoTimer) clearInterval(this.photoTimer);
      clearInterval(ttsPollInterval);
    });
  }
}
