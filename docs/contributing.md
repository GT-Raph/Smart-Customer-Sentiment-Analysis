# Contributing

- Keep the application single-installation and non-SaaS: do not add tenants,
  subscriptions, billing, plans, or commercial usage quotas to this branch.
- Use Python 3.10 and keep API/dashboard dependencies separate from the inference
  worker environment.
- Never commit `.env`, device keys, database credentials, raw face images,
  embeddings, production logs, or exports.
- Add tests for authentication, branch access, upload validation, job states, and
  model-output normalization.
- Run root tests, Django tests, `manage.py makemigrations --check`, and Django's
  deployment checks before committing.
- Represent database changes with Django migrations.
- Keep production code in importable modules and research notebooks under `research/`.
