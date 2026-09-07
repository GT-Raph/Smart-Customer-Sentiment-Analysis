# Non-SaaS conversion

- Removed organization tenancy from users, branches, devices, visitors, and snapshots.
- Removed plans, subscription states, billing references, monthly usage, and quotas.
- Kept branch-level dashboard permissions for local staff.
- Restored the polished SaaS dashboard presentation for the self-hosted edition,
  including the desktop sidebar, mobile navigation, analytics, reports, settings,
  and login experience, without restoring tenancy or billing behavior.
- Replaced PostgreSQL-specific configuration and ingestion SQL with a shared
  XAMPP MySQL/MariaDB database setup for Django, FastAPI, and the RQ worker.
- Kept revocable per-device API keys and per-device rate limiting.
- Made device PC names and visitor face IDs unique within the installation.
- Added a migration that consolidates duplicate visitor identities and safely renames
  duplicate device PC names before removing the SaaS tables.
- Updated the API, worker, administration screens, tests, and operator documentation.

The application remains self-hosted and has no payment-provider or customer-onboarding
integration.
