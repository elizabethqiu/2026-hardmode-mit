-- 003_web_app.sql — Schema additions for the Enoki web application.
-- Adds auth integration trigger, conversation history, study plans,
-- user goals, nudge log, invite codes, and RLS policies.

-- Auto-create users row when someone signs up via Supabase Auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, display_name)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Invite codes for groves
ALTER TABLE groves ADD COLUMN IF NOT EXISTS invite_code TEXT UNIQUE;

-- Conversation history for Personal Claude
CREATE TABLE IF NOT EXISTS conversation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_convo_user ON conversation_messages(user_id, created_at);

-- Study plans (web version, replaces local SQLite)
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

-- User goals (set by Claude's set_goal tool)
CREATE TABLE IF NOT EXISTS user_goals (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  description TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Nudge log (web version)
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

-- RLS: Users can read themselves and grove co-members
CREATE POLICY users_self ON users FOR ALL USING (id = auth.uid());
CREATE POLICY users_grove ON users FOR SELECT USING (
  id IN (SELECT user_id FROM grove_members WHERE grove_id IN
    (SELECT grove_id FROM grove_members WHERE user_id = auth.uid()))
);

-- Groves: members can read, creator can insert
CREATE POLICY grove_member_read ON groves FOR SELECT USING (
  id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
CREATE POLICY grove_public_invite ON groves FOR SELECT USING (invite_code IS NOT NULL);
CREATE POLICY grove_create ON groves FOR INSERT WITH CHECK (created_by = auth.uid());
CREATE POLICY grove_update ON groves FOR UPDATE USING (created_by = auth.uid());

-- Grove members
CREATE POLICY grove_members_read ON grove_members FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
CREATE POLICY grove_members_join ON grove_members FOR INSERT WITH CHECK (user_id = auth.uid());

-- Focus states
CREATE POLICY focus_self ON focus_states FOR ALL USING (user_id = auth.uid());
CREATE POLICY focus_grove ON focus_states FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);

-- Conversation messages
CREATE POLICY convo_self ON conversation_messages FOR ALL USING (user_id = auth.uid());

-- Study plans and sprints
CREATE POLICY plans_self ON study_plans FOR ALL USING (user_id = auth.uid());
CREATE POLICY sprints_self ON study_sprints FOR ALL USING (
  plan_id IN (SELECT id FROM study_plans WHERE user_id = auth.uid())
);

-- Goals and nudge log
CREATE POLICY goals_self ON user_goals FOR ALL USING (user_id = auth.uid());
CREATE POLICY nudge_self ON nudge_log FOR ALL USING (user_id = auth.uid());

-- Grove sprints and nudges
CREATE POLICY sprints_grove ON sprints FOR ALL USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
CREATE POLICY nudges_grove ON grove_nudges FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
CREATE POLICY nudges_insert ON grove_nudges FOR INSERT WITH CHECK (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);

-- Focus history
CREATE POLICY focus_history_self ON focus_history FOR ALL USING (user_id = auth.uid());
CREATE POLICY focus_history_grove ON focus_history FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);

-- Daily summaries
CREATE POLICY summaries_grove ON daily_summaries FOR SELECT USING (
  grove_id IN (SELECT grove_id FROM grove_members WHERE user_id = auth.uid())
);
