-- Focus history: timestamped snapshots for daily digest analysis.
-- Each orchestrator inserts once per ~60s. Used by daily-digest edge function.

CREATE TABLE IF NOT EXISTS focus_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    grove_id UUID REFERENCES groves(id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN ('FOCUSED', 'IDLE', 'DOZING', 'AWAY')),
    focus_score NUMERIC(3,2) DEFAULT 0.0,
    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_focus_history_grove_date
    ON focus_history(grove_id, recorded_at);

CREATE INDEX IF NOT EXISTS idx_focus_history_user_date
    ON focus_history(user_id, recorded_at);

-- RPC function for initial member fetch with display names.
-- Called by the orchestrator on startup (fallback: direct join query).
CREATE OR REPLACE FUNCTION get_grove_members_with_names(p_grove_id UUID)
RETURNS TABLE (
    user_id UUID,
    display_name TEXT,
    state TEXT,
    focus_score NUMERIC,
    session_minutes INTEGER,
    today_focus_hours NUMERIC,
    in_sprint BOOLEAN,
    mushroom_mood TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        fs.user_id,
        u.display_name,
        fs.state,
        fs.focus_score,
        fs.session_minutes,
        fs.today_focus_hours,
        fs.in_sprint,
        fs.mushroom_mood
    FROM focus_states fs
    JOIN users u ON u.id = fs.user_id
    WHERE fs.grove_id = p_grove_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Auto-cleanup: delete focus_history older than 30 days.
-- Run manually or via pg_cron if available.
-- DELETE FROM focus_history WHERE recorded_at < now() - INTERVAL '30 days';
