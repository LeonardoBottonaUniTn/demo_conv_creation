-- Allow different users to upload files with the same name by scoping uniqueness to rel_path.
ALTER TABLE public.files DROP CONSTRAINT IF EXISTS files_name_key;

CREATE UNIQUE INDEX IF NOT EXISTS files_rel_path_unique ON public.files (rel_path);

CREATE INDEX IF NOT EXISTS files_created_by_idx ON public.files (created_by);
