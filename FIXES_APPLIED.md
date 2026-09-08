# Fixes applied

## Completed

- Restored the original multi-bank SaaS domain: banks, branches, tenant users,
  visitors, snapshots, bank settings, and user preferences.
- Pointed Django and FastAPI at the same Supabase PostgreSQL database through
  root `.env` `DB_*` settings.
- Preserved the polished SaaS dashboard and tenant navigation from `main`.
- Restored bank-scoped upload authentication with hashed API keys.
- Restored automatic branch selection from the teller PC-name prefix.
- Restored synchronous DeepFace expression analysis and Supabase persistence.
- Added bounded image uploads, decoded-image validation, and private image paths.
- Kept the separate `non-saas` branch unmerged.
- Added Docker development services, tests, and current deployment guidance.

## Verified

- Django recognizes both existing `monitor` migrations with no model changes.
- The supplied Supabase database is reachable by Django and FastAPI.
- Existing bank, branch, user, and analytics records load in the SaaS dashboard.
- The supplied bank upload credential matches its stored hash.
- Django and FastAPI both start successfully and return HTTP 200 responses.
- Fifteen API/config tests and seven Django tenant tests pass.

## Still required before a commercial public launch

- Rotate credentials that were shared outside the deployment secret store.
- Move captured images to private object storage for multi-host deployment.
- Add billing, subscriptions, customer onboarding, and retention controls.
- Add centralized logs, metrics, alerts, backups, and recovery exercises.
- Complete legal/privacy review and validate the model in the intended setting.
- Add liveness/anti-spoofing if persistent visitor matching is used.
