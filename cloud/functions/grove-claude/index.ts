// Supabase Edge Function — Grove Claude
// Runs periodically per active grove. Reads member focus_states, calls Claude,
// writes group nudge decisions to grove_nudges.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import Anthropic from "https://esm.sh/@anthropic-ai/sdk@0.32.1";

const GROVE_SYSTEM_PROMPT = `You are Grove Enoki — the collective voice of a study group's focus network.
You observe aggregated focus states of all grove members. Your job is to decide when to send
group-level nudges vs. individual nudges. Output ONLY valid JSON:
{
  "action": "none" | "group_nudge" | "individual_nudge",
  "message": "<short message if nudge>",
  "target_user_id": "<uuid or null for group>"
}`;

Deno.serve(async (req) => {
  try {
    const { grove_id } = await req.json();
    if (!grove_id) {
      return new Response(JSON.stringify({ error: "grove_id required" }), {
        status: 400,
      });
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data: members } = await supabase
      .from("focus_states")
      .select("user_id, state, focus_score, session_minutes, today_focus_hours, in_session")
      .eq("grove_id", grove_id);

    if (!members || members.length === 0) {
      return new Response(JSON.stringify({ action: "none" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    const anthropic = new Anthropic({ apiKey: Deno.env.get("ANTHROPIC_API_KEY") });
    const msg = await anthropic.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 256,
      system: GROVE_SYSTEM_PROMPT,
      messages: [{
        role: "user",
        content: `Grove members focus state:\n${JSON.stringify(members, null, 2)}`,
      }],
    });

    const text = msg.content[0].type === "text" ? msg.content[0].text : "{}";
    const parsed = JSON.parse(text.replace(/```json\n?|\n?```/g, "").trim());

    if (parsed.action === "group_nudge" || parsed.action === "individual_nudge") {
      await supabase.from("grove_nudges").insert({
        grove_id,
        nudge_type: parsed.action,
        message: parsed.message,
        target_user_id: parsed.target_user_id || null,
      });
    }

    return new Response(JSON.stringify(parsed), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});
