-- Storage policies for the private user-files bucket.
INSERT INTO storage.buckets (id, name, public)
VALUES ('user-files', 'user-files', false)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "Users can read own storage objects" ON storage.objects;
DROP POLICY IF EXISTS "Users can upload own storage objects" ON storage.objects;
DROP POLICY IF EXISTS "Users can update own storage objects" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own storage objects" ON storage.objects;

CREATE POLICY "Users can read own storage objects"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'user-files'
  AND name LIKE auth.uid()::text || '/%'
);

CREATE POLICY "Users can upload own storage objects"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'user-files'
  AND name LIKE auth.uid()::text || '/%'
);

CREATE POLICY "Users can update own storage objects"
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'user-files'
  AND name LIKE auth.uid()::text || '/%'
)
WITH CHECK (
  bucket_id = 'user-files'
  AND name LIKE auth.uid()::text || '/%'
);

CREATE POLICY "Users can delete own storage objects"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'user-files'
  AND name LIKE auth.uid()::text || '/%'
);
