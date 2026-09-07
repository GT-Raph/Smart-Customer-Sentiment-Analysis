# Security and privacy baseline

- Raw face images are private and are deleted after analysis by default.
- Every camera/device uses a separate revocable API key.
- API keys are stored only as SHA-256 hashes and are displayed once on creation.
- Non-administrator dashboard users without an active branch assignment are denied.
- Face identification is disabled by default.
- Do not use expression results as proof of a person's internal emotional state.
- Obtain legal/privacy review, provide notice, document consent or another valid
  lawful basis, and configure retention before any live deployment.
- Put the dashboard and API behind HTTPS and a managed reverse proxy/WAF.
- Add object storage and signed URLs before a multi-host production deployment.
