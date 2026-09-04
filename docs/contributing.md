# Contributing

- Use Python 3.10 and keep API/dashboard dependencies separate from the heavy
  inference-worker environment.
- Never commit `.env`, device keys, database credentials, raw face images,
  embeddings, production logs or customer exports.
- Add tests for authentication, tenant boundaries, upload validation, job state
  transitions and model-output normalization.
- Run `python -m compileall`, the root unit tests, Django tests,
  `manage.py makemigrations --check`, and `manage.py check --deploy`.
- Database changes must be represented by Django migrations. Do not add a
  second table-creation implementation to the API or a notebook.
- Production code belongs in importable modules. Notebooks belong in
  `research/` and must have outputs and secrets removed.
- Document model changes and validate them against consented data matching the
  intended cameras, lighting and user population.
