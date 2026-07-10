-- Add LLM provider selection to per-user settings
ALTER TABLE public.user_settings
    ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'groq';
