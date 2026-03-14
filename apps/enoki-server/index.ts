import { anthropic } from "./claude";
import { runVisionCheck, type VisionRequestBody } from "./vision";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export type AttentionState = "focused" | "distracted";

type SummaryRequestBody = {
  task?: string;
  focusMinutes?: number;
  driftCount?: number;
  longestFocusStreakMinutes?: number;
  finalState?: string;
};

type CoachRequestBody = {
  task?: string;
  secondsAway?: number;
  driftCount?: number;
  currentState?: string;
};

let latestAttentionState: AttentionState = "focused";

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
    },
  });
}

export async function handleRequest(req: Request): Promise<Response> {
  try {
    const url = new URL(req.url);

    if (req.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    if (url.pathname === "/" && req.method === "GET") {
      return jsonResponse({ ok: true, message: "enoki server is running" });
    }

    if (url.pathname === "/health" && req.method === "GET") {
      return jsonResponse({
        ok: true,
        message: "enoki claude server is running",
      });
    }

    if (url.pathname === "/attention" && req.method === "GET") {
      return jsonResponse({ state: latestAttentionState });
    }

    if (url.pathname === "/attention" && req.method === "POST") {
      const body = (await req.json()) as { state?: AttentionState };

      if (body.state !== "focused" && body.state !== "distracted") {
        return jsonResponse({ error: "invalid state" }, 400);
      }

      latestAttentionState = body.state;
      console.log("attention state updated:", latestAttentionState);

      return jsonResponse({ ok: true, state: latestAttentionState });
    }

    if (url.pathname === "/vision-check" && req.method === "POST") {
      if (!process.env.ANTHROPIC_API_KEY) {
        return jsonResponse(
          { error: "missing ANTHROPIC_API_KEY in .env" },
          500,
        );
      }

      const body = (await req.json()) as VisionRequestBody;
      const task = body.task?.trim() || "unknown";
      const image = body.image?.trim() || "";

      if (!image) {
        return jsonResponse({ error: "missing image" }, 400);
      }

      const result = await runVisionCheck(task, image);
      return jsonResponse({ result });
    }

    if (url.pathname === "/summary" && req.method === "POST") {
      if (!process.env.ANTHROPIC_API_KEY) {
        return jsonResponse(
          { error: "missing ANTHROPIC_API_KEY in .env" },
          500,
        );
      }

      const body = (await req.json()) as SummaryRequestBody;

      const task = body.task?.trim() || "untitled task";
      const focusMinutes = body.focusMinutes ?? 0;
      const driftCount = body.driftCount ?? 0;
      const longestFocusStreakMinutes = body.longestFocusStreakMinutes ?? 0;
      const finalState = body.finalState ?? "dormant";

      const prompt = `
you are writing a short, gentle productivity reflection for a wearable focus companion app called enoki.

session data:
- task: ${task}
- focus minutes: ${focusMinutes}
- attention drifts: ${driftCount}
- longest focus streak in minutes: ${longestFocusStreakMinutes}
- final mushroom state: ${finalState}

instructions:
- keep the tone warm, supportive, and concise
- avoid sounding judgmental
- write 3 short parts:
  1. one sentence recap
  2. one sentence about enoki's state
  3. one gentle suggestion for the next session
- keep total output under 90 words
- make it feel encouraging, soft, and slightly magical
`.trim();

      const message = await anthropic.messages.create({
        model: "claude-sonnet-4-6", // FIX: updated from claude-sonnet-4-5
        max_tokens: 220,
        messages: [{ role: "user", content: prompt }],
      });

      const textBlocks = message.content.filter(
        (
          block,
        ): block is Extract<
          (typeof message.content)[number],
          { type: "text" }
        > => block.type === "text",
      );

      const summary =
        textBlocks
          .map((block) => block.text)
          .join("\n")
          .trim() ||
        "enoki noticed your session and is ready for another gentle round.";

      return jsonResponse({ summary });
    }

    if (url.pathname === "/coach" && req.method === "POST") {
      if (!process.env.ANTHROPIC_API_KEY) {
        return jsonResponse(
          { error: "missing ANTHROPIC_API_KEY in .env" },
          500,
        );
      }

      const body = (await req.json()) as CoachRequestBody;

      const task = body.task?.trim() || "your task";
      const secondsAway = body.secondsAway ?? 0;
      const driftCount = body.driftCount ?? 0;
      const currentState = body.currentState ?? "warning";

      const prompt = `
you are a gentle live coach for a focus companion app called enoki.

current state:
- task: ${task}
- seconds away from task: ${secondsAway}
- total drifts so far: ${driftCount}
- current mushroom state: ${currentState}

instructions:
- write one short supportive nudge
- under 24 words
- do not shame the user
- sound calm, warm, and encouraging
- optionally mention enoki once
- help the user return to the task
`.trim();

      const message = await anthropic.messages.create({
        model: "claude-sonnet-4-6", // FIX: updated from claude-sonnet-4-5
        max_tokens: 80,
        messages: [{ role: "user", content: prompt }],
      });

      const textBlocks = message.content.filter(
        (
          block,
        ): block is Extract<
          (typeof message.content)[number],
          { type: "text" }
        > => block.type === "text",
      );

      const coach =
        textBlocks
          .map((block) => block.text)
          .join("\n")
          .trim() || "enoki believes you can gently return to your task.";

      return jsonResponse({ coach });
    }

    return jsonResponse({ error: "not found" }, 404);
  } catch (error) {
    console.error("handleRequest fatal error:", error);
    return jsonResponse({ error: "internal server error" }, 500);
  }
}
