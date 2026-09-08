# Security and privacy baseline

- Every upload requires `X-Bank-Code` and `X-API-Key`.
- Bank API keys are stored as hashes and the raw value is shown only when set.
- Branch selection is server-controlled from an active PC-name prefix.
- Dashboard queries and private image responses are tenant-scoped.
- Users without a valid bank/branch assignment receive no cross-tenant data.
- Supabase connections require TLS (`DB_SSLMODE=require`).
- `.env`, captured images, embeddings, logs, and exports must never be committed.
- Teller machines receive only client credentials, never database or Django
  secrets.
- Put both web services behind HTTPS and rotate any exposed credential.
- Treat face images and embeddings as sensitive data with documented notice,
  access, deletion, and retention controls.
- Do not present inferred expressions as proof of a person's internal state.
- Add liveness/anti-spoofing before relying on persistent face matching.
