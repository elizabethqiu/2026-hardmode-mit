-- ============================================================
-- ENOKI: Combined migrations (001 + 002 + 003)
-- Run this entire script in the Supabase SQL Editor
-- ============================================================

-- === 001_initial.sql ===

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
    summary_date DATE NOT NULL,
    digest TEXT,
    summary_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (grove_id, summary_date)
);

CREATE INDEX IF NOT EXISTS idx_focus_states_grove ON focus_states(grove_id);
CREATE INDEX IF NOT EXISTS idx_focus_states_updated ON focus_states(updated_at);
CREATE INDEX IF NOT EXISTS idx_sprints_grove_status ON sprints(grove_id, status);
CREATE INDEX IF NOT EXISTS idx_grove_nudges_grove ON grove_nudges(grove_id);

-- === 002_focus_history.sql ===

CREATE TABLE IF NOT EXISTS focus_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    grove_id UUID REFERENCES groves(id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN ('FOCUSED', 'IDLE', 'DOZING', 'AWAY')),
    focus_score NUMERIC(3,2) DEFAULT 0.0,
    recorded_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_focus_history_grove_date
    ON focus_history(grove_id, recorded_at);

CREATE INDEX IF NOT EXISTS idx_focus_history_user_date
    ON focus_history(user_id, recorded_at);

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

-- === 003_web_app.sql ===

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, display_name)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

ALTER TABLE groves ADD COLUMN IF NOT EXISTS invite_code TEXT UNIQUE;

CREATE TABLE IF NOT EXISTS conversation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_convo_user ON conversation_messages(user_id, created_at);

CREATE TABLE IF NOT EXISTS study_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  plan_date DATE NOT NULL,
  plan_summary TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (user_id, plan_date)
);

CREATE TABLE IF NOT EXISTS study_sprints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID REFERENCES study_plans(id) ON DELETE CASCADE,
  topic TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL,
  sprint_order INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'active', 'completed', 'skipped')),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  actual_minutes NUMERIC(6,1) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_goals (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  description TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS nudge_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  worked BOOLEAN NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE groves ENABLE ROW LEVEL SECURITY;
ALTER TABLE grove_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE focus_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE sprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE grove_nudges ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_sprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE nudge_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE focus_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_summaries ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY users_self ON users FOR ALL USING (id = auth.uid());
CREATE POLICY users_grove ON users FOR SELECT USING (
  id IN (SELECT user_id FROM grove_members WHERE grove_id IN
    (SELECT grove_id FROM grove_members WHERE user_id = auth.uid()))
);

CREATE POLICY grove_member_read ON groves FOR SELECT USING (
  id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
CREATE POLICY grove_public_invite ON groves FOR SELECT USING (invite_code IS NOT NULL);
CREATE POLICY grove_create ON groves FOR INSERT WITH CHECK (created_by = auth.uid());
CREATE POLICY grove_update ON groves FOR UPDATE USING (created_by = auth.uid());

CREATE POLICY grove_members_read ON grove_members FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
CREATE POLICY grove_members_join ON grove_members FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY focus_self ON focus_states FOR ALL USING (user_id = auth.uid());
CREATE POLICY focus_grove ON focus_states FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);

CREATE POLICY convo_self ON conversation_messages FOR ALL USING (user_id = auth.uid());

CREATE POLICY plans_self ON study_plans FOR ALL USING (user_id = auth.uid());
CREATE POLICY sprints_self ON study_sprints FOR ALL USING (
  plan_id IN (SELECT id FROM study_plans WHERE user_id = auth.uid())
);

CREATE POLICY goals_self ON user_goals FOR ALL USING (user_id = auth.uid());
CREATE POLICY nudge_self ON nudge_log FOR ALL USING (user_id = auth.uid());

CREATE POLICY sprints_grove ON sprints FOR ALL USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
CREATE POLICY nudges_grove ON grove_nudges FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
CREATE POLICY nudges_insert ON grove_nudges FOR INSERT WITH CHECK (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);

CREATE POLICY focus_history_self ON focus_history FOR ALL USING (user_id = auth.uid());
CREATE POLICY focus_history_grove ON focus_history FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);

CREATE POLICY summaries_grove ON daily_summaries FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);

-- Enable Realtime for focus_states, grove_nudges, sprints
ALTER PUBLICATION supabase_realtime ADD TABLE focus_states;
ALTER PUBLICATION supabase_realtime ADD TABLE grove_nudges;
ALTER PUBLICATION supabase_realtime ADD TABLE sprints;
