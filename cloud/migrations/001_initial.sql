-- Enoki Cloud Schema — Supabase
-- Users, groves, focus states, sprints, daily summaries

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS groves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_by UUID REFERENCES users(id),
    daily_goal_hours NUMERIC(4,2) DEFAULT 3.0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS grove_members (
    grove_id UUID REFERENCES groves(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT now(),
    led_position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (grove_id, user_id)
);

CREATE TABLE IF NOT EXISTS focus_states (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    grove_id UUID REFERENCES groves(id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN ('FOCUSED', 'IDLE', 'DOZING', 'AWAY')),
    focus_score NUMERIC(3,2) DEFAULT 0.0,
    session_minutes INTEGER DEFAULT 0,
    today_focus_hours NUMERIC(5,2) DEFAULT 0.0,
    in_sprint BOOLEAN DEFAULT false,
    mushroom_mood TEXT,
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS sprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grove_id UUID REFERENCES groves(id) ON DELETE CASCADE,
    proposed_by UUID REFERENCES users(id),
    duration_minutes INTEGER NOT NULL,
    started_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('proposed', 'active', 'completed', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS grove_nudges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grove_id UUID REFERENCES groves(id) ON DELETE CASCADE,
    nudge_type TEXT NOT NULL,
    message TEXT,
    target_user_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS daily_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grove_id UUID REFERENCES groves(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    summary_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (grove_id, date)
);

CREATE INDEX IF NOT EXISTS idx_focus_states_grove ON focus_states(grove_id);
CREATE INDEX IF NOT EXISTS idx_focus_states_updated ON focus_states(updated_at);
CREATE INDEX IF NOT EXISTS idx_sprints_grove_status ON sprints(grove_id, status);
CREATE INDEX IF NOT EXISTS idx_grove_nudges_grove ON grove_nudges(grove_id);
