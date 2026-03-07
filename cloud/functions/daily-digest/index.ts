// Supabase Edge Function — Daily Digest
// Triggered at end of day (cron). Aggregates day's data, calls Insight Claude, writes summary.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import Anthropic from "https://esm.sh/@anthropic-ai/sdk@0.32.1";

const INSIGHT_PROMPT = `You are Enoki Insight — you analyze a day's focus data for a study grove.
Given the aggregated data, produce a brief (2-3 sentence) daily summary. Output ONLY valid JSON:
{
  "summary": "<human-readable summary>",
  "highlights": ["<highlight1>", "<highlight2>"]
}`;

Deno.serve(async (req) => {
  try {
    const { grove_id, date } = await req.json();
    if (!grove_id || !date) {
      return new Response(JSON.stringify({ error: "grove_id and date required" }), {
        status: 400,
      });
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data: states } = await supabase
      .from("focus_states")
      .select("*")
      .eq("grove_id", grove_id);

    const anthropic = new Anthropic({ apiKey: Deno.env.get("ANTHROPIC_API_KEY") });
    const msg = await anthropic.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 512,
      system: INSIGHT_PROMPT,
      messages: [{
        role: "user",
        content: `Date: ${date}\nFocus data:\n${JSON.stringify(states || [], null, 2)}`,
      }],
    });

    const text = msg.content[0].type === "text" ? msg.content[0].text : "{}";
    const parsed = JSON.parse(text.replace(/```json\n?|\n?```/g, "").trim());

    await supabase.from("daily_summaries").upsert({
      grove_id,
      date,
      summary_json: parsed,
    }, { onConflict: "grove_id,date" });

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
