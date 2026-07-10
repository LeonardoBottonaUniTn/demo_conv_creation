-- Per-user LLM settings (required by /api/settings in backend/main.py)
CREATE TABLE IF NOT EXISTS public.user_settings (
    user_id     uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    api_key     text,
    model       text,
    provider    text NOT NULL DEFAULT 'groq',
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

GRANT ALL ON TABLE public.user_settings TO anon;
GRANT ALL ON TABLE public.user_settings TO authenticated;
GRANT ALL ON TABLE public.user_settings TO service_role;
