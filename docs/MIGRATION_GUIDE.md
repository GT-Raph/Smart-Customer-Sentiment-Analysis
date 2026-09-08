# Database migration guide

The `main` branch is aligned with the existing multi-bank Supabase schema. Its
authoritative Django migrations are:

1. `monitor.0001_initial`
2. `monitor.0002_bank_api_key_rotated_at_alter_bank_code_and_more`

Before deploying a code or schema change:

1. Create and verify a Supabase backup.
2. Run `python manage.py showmigrations monitor` against the intended database.
3. Run `python manage.py makemigrations --check --dry-run`.
4. Review generated SQL for any new migration before applying it.
5. Run `python manage.py migrate` during a controlled deployment window.
6. Test a platform administrator, bank administrator, branch user, and upload
   request after deployment.

Never manually recreate Django-owned tables in phpMyAdmin or the Supabase SQL
editor. Do not copy the `non-saas` MySQL schema into the SaaS database or merge
its database configuration into `main`.
