# Migration to the non-SaaS edition

The non-SaaS schema represents one organization per installation. Migration
`0002_remove_saas_tenancy` removes organization, plan, subscription, billing, and
monthly usage data while retaining branches, users, devices, visitors, and snapshots.

Before migration:

1. Back up PostgreSQL and verify the backup can be restored.
2. Stop the API and worker so no snapshots are created during migration.
3. Confirm that every normal dashboard user is assigned to the correct branch.
4. Run `python manage.py migrate` from `emotion_dashboard/`.
5. Start the dashboard, API, and worker and run a test capture.

If different organizations used the same device PC name, the migration appends a
record ID to later duplicates. Visitors with the same face ID are consolidated and
their snapshots are retained. Review device names after migration.

Organization and billing metadata is intentionally discarded. Keep the pre-migration
backup if those records must be retained for audit purposes. For the cleanest
installation, use a new database and import only reviewed analytics.
