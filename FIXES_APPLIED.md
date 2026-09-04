# Fixes applied

## Completed in this revision

- Removed all committed database credentials and the committed Django secret.
- Removed public and debug media exposure of raw face images.
- Replaced the global optional API key with one-time, revocable device keys.
- Added organisations, subscription states, branches, devices and monthly usage.
- Added an atomic monthly quota check before accepting analysis jobs.
- Replaced the conflicting snapshot schemas with one Django-managed schema.
- Replaced the polling processing notebook with a Redis/RQ worker.
- Kept DeepFace/TensorFlow out of the FastAPI web process.
- Added bounded upload reads, real file-format checks, dimension limits and rate limits.
- Added job status, safe client errors and failed-job recording.
- Disabled persistent biometric matching by default.
- Added short-lived visit sessions for privacy-preserving visitor counts.
- Added organisation-scoped nearest-neighbour matching when identification is enabled.
- Added default raw-image deletion after successful processing.
- Added a low-rate camera client with offline queue limits.
- Added Docker development deployment, CI and dependency-update configuration.
- Added migration, deployment, API, architecture and security documentation.

## Verified

- Python compilation completed successfully.
- 11 API/worker tests pass.
- 7 Django access/onboarding tests pass.
- Django reports no pending model migrations.
- Django's production deployment check reports no issues with production-like settings.
- The FastAPI OpenAPI schema builds successfully without loading DeepFace.
- No previously exposed credential, database host or Django secret remains in the revised tree.

## Still required before a commercial public launch

- Rotate the original database password and purge it from the private Git history.
- Use a new database or carefully migrate reviewed data from the incompatible prototype schema.
- Replace the single-host shared image volume with private object storage.
- Integrate Stripe, Paystack or another payment provider with subscription webhooks.
- Add customer self-service onboarding, invoices, exports, deletion and retention controls.
- Add centralized logs, metrics, tracing, alerts, backups and recovery drills.
- Conduct legal/privacy review and a model validation study using consented target-environment data.
- Add liveness/anti-spoofing before enabling persistent identity recognition.
