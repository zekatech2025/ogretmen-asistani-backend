-- Bu SQL'i Supabase panelinde SQL Editor'da çalıştırın

-- Kullanıcı kota tablosu
CREATE TABLE IF NOT EXISTS user_quotas (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  prompts_used  INTEGER DEFAULT 0,
  prompts_limit INTEGER DEFAULT 1000,
  created_at    TIMESTAMP DEFAULT NOW(),
  updated_at    TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id)
);

-- RLS (Row Level Security) aç
ALTER TABLE user_quotas ENABLE ROW LEVEL SECURITY;

-- Kullanıcı sadece kendi verisini okuyabilir
CREATE POLICY "Kullanici kendi kotasini okur"
  ON user_quotas FOR SELECT
  USING (auth.uid() = user_id);

-- Sadece service role yazabilir (backend)
CREATE POLICY "Service role yazar"
  ON user_quotas FOR ALL
  USING (auth.role() = 'service_role');

-- Prompt sayacını artıran fonksiyon
CREATE OR REPLACE FUNCTION increment_prompts_used(p_user_id UUID)
RETURNS void AS $$
BEGIN
  UPDATE user_quotas
  SET prompts_used = prompts_used + 1,
      updated_at = NOW()
  WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Sohbet geçmişi tablosu (opsiyonel, ilerleyen aşama için)
CREATE TABLE IF NOT EXISTS chat_sessions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title      VARCHAR(500),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Kullanici kendi sohbetini gorur"
  ON chat_sessions FOR ALL
  USING (auth.uid() = user_id);
