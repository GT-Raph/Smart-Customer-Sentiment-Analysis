# Contributing

- Use Python 3.10 for compatibility with the pinned analysis dependencies.
- Never commit `.env`, credentials, raw face images, embeddings, production
  logs, or customer exports.
- Preserve bank and branch tenant filters in every dashboard/API change.
- Represent relational schema changes with reviewed Django migrations.
- Keep production processing in importable Python modules; notebooks under
  `research/` are historical experiments only.
- Add tests for authentication, tenant boundaries, PC-prefix matching, upload
  validation, and model-output normalization.
- Before committing, run `python -m compileall`, root unit tests, Django tests,
  `python emotion_dashboard/manage.py makemigrations --check`, and
  `python emotion_dashboard/manage.py check --deploy` from the repository root.
- Document model changes and validate them against consented data representative
  of the intended cameras, lighting, and population.
