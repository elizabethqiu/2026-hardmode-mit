import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  try {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const body = await request.json();

    const { error } = await supabase.from("focus_states").upsert(
      {
        user_id: user.id,
        grove_id: body.grove_id || null,
        state: body.state || "AWAY",
        focus_score: body.focus_score ?? 0,
        session_minutes: body.session_minutes ?? 0,
        today_focus_hours: body.today_focus_hours ?? 0,
        in_sprint: body.in_sprint ?? false,
        mushroom_mood: body.mushroom_mood || "watchful",
        updated_at: new Date().toISOString(),
      },
      { onConflict: "user_id" }
    );

    if (error) return NextResponse.json({ error: error.message }, { status: 500 });

    // Also insert into focus_history for analytics
    if (body.grove_id) {
      await supabase.from("focus_history").insert({
        user_id: user.id,
        grove_id: body.grove_id,
        state: body.state || "AWAY",
        focus_score: body.focus_score ?? 0,
      });
    }

    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
