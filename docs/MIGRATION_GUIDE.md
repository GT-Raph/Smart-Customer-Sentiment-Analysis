# Migration from the prototype database

The prototype used several incompatible versions of `captured_snapshots`. The
new version deliberately uses a clean, migration-owned schema.

1. Back up the current database before doing anything.
2. Rotate the exposed database password and Django secret key.
3. For the safest upgrade, use a new Supabase project/database for this version.
4. Run `python manage.py migrate` from `emotion_dashboard/`.
5. Create an organisation, branch, administrator and device.
6. Import only reviewed historical analytics. Do not bulk-copy raw face images
   or embeddings unless you have a valid consent and retention basis.

Do not point the new code at the old production table and run destructive SQL.
The old table should remain read-only until any required migration is verified.
