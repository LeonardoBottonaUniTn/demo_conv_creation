-- Per-user annotation schema (custom fields and labels for the annotation tool)
ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS annotation_schema jsonb;
