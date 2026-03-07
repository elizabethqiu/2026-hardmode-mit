/**
 * Shared interfaces for Enoki MiniApp ↔ Orchestrator communication
 */

export interface GlassesPayload {
  transcription?: string;
  photo_base64?: string;
  wearing?: boolean;
  button_pressed?: boolean;
  timestamp?: number;
}

export interface TTSRequest {
  text: string;
  priority?: number;
}
