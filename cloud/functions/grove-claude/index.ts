// Supabase Edge Function — Grove Claude
// Runs periodically per active grove. Reads member focus_states, calls Claude,
// writes decisions to grove_nudges and/or sprints.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import Anthropic from "https://esm.sh/@anthropic-ai/sdk@0.32.1";

const GROVE_SYSTEM_PROMPT = `You are Grove Enoki — the collective consciousness of a study group's mushroom network.
You observe the focus state of all grove members. Your job is to foster group accountability
and celebrate collective focus. You make ONE decision per invocation.

Rules:
- If everyone is focused, say nothing (action: "none") unless a sprint just completed.
- If 1 member is idle while others focus, send an individual nudge to that member.
- If multiple members are idle, send a group nudge to rally everyone.
- If the whole grove has been idle for a while, propose a sprint.
- If a sprint was just completed by the group, celebrate.
- Be supportive, never judgmental. Use "we" language for group nudges.
- Keep messages under 2 sentences.

Output ONLY valid JSON matching this schema:
{
  "action": "none" | "group_nudge" | "individual_nudge" | "celebration" | "propose_sprint",
  "message": "<short motivational message, or empty string if action is none>",
  "target_user_id": "<uuid of individual to nudge, or null>",
  "sprint_duration_minutes": <int, only if action is propose_sprint, typically 25>
}`;

Deno.serve(async (req) => {
  try {
    const { grove_id } = await req.json();
    if (!grove_id) {
      return new Response(JSON.stringify({ error: "grove_id required" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Fetch member states with display names
    const { data: members } = await supabase
      .from("focus_states")
      .select("user_id, state, focus_score, session_minutes, today_focus_hours, in_sprint, users!inner(display_name)")
      .eq("grove_id", grove_id);

    if (!members || members.length === 0) {
      return new Response(JSON.stringify({ action: "none" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // Flatten display_name into each record
    const enriched = members.map((m: any) => ({
      user_id: m.user_id,
      display_name: m.users?.display_name ?? "Unknown",
      state: m.state,
      focus_score: m.focus_score,
      session_minutes: m.session_minutes,
      today_focus_hours: m.today_focus_hours,
      in_sprint: m.in_sprint,
    }));

    // Check recent nudges to avoid spamming (skip if nudged in last 2 minutes)
    const { data: recentNudges } = await supabase
      .from("grove_nudges")
      .select("created_at")
      .eq("grove_id", grove_id)
      .order("created_at", { ascending: false })
      .limit(1);

    if (recentNudges && recentNudges.length > 0) {
      const lastNudge = new Date(recentNudges[0].created_at).getTime();
      if (Date.now() - lastNudge < 120_000) {
        return new Response(JSON.stringify({ action: "none", reason: "cooldown" }), {
          headers: { "Content-Type": "application/json" },
        });
      }
    }

    // Check active sprint
    const { data: activeSprints } = await supabase
      .from("sprints")
      .select("id, status, duration_minutes, started_at")
      .eq("grove_id", grove_id)
      .eq("status", "active")
      .limit(1);

    const sprintContext = activeSprints && activeSprints.length > 0
      ? `Active sprint: ${activeSprints[0].duration_minutes} min, started at ${activeSprints[0].started_at}`
      : "No active sprint.";

    const anthropic = new Anthropic({ apiKey: Deno.env.get("ANTHROPIC_API_KEY") });
    const msg = await anthropic.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 256,
      system: GROVE_SYSTEM_PROMPT,
      messages: [{
        role: "user",
        content: `Grove members:\n${JSON.stringify(enriched, null, 2)}\n\n${sprintContext}`,
      }],
    });

    const text = msg.content[0].type === "text" ? msg.content[0].text : "{}";
    const parsed = JSON.parse(text.replace(/```json\n?|\n?```/g, "").trim());

    // Write nudge to grove_nudges
    if (parsed.action === "group_nudge" || parsed.action === "individual_nudge" || parsed.action === "celebration") {
      await supabase.from("grove_nudges").insert({
        grove_id,
        nudge_type: parsed.action,
        message: parsed.message || "",
        target_user_id: parsed.target_user_id || null,
      });
    }

    // Propose sprint by inserting into sprints table
    if (parsed.action === "propose_sprint") {
      const duration = parsed.sprint_duration_minutes || 25;
      await supabase.from("sprints").insert({
        grove_id,
        proposed_by: null, // proposed by Grove Claude, not a user
        duration_minutes: duration,
        status: "proposed",
      });

      // Also write a nudge so members see the proposal
      await supabase.from("grove_nudges").insert({
        grove_id,
        nudge_type: "group_nudge",
        message: parsed.message || `Grove Claude proposes a ${duration}-minute focus sprint. Let's go!`,
        target_user_id: null,
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
