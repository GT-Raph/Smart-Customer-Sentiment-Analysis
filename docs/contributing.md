# Contributing

Thank you for contributing! This document outlines a minimal workflow and expectations.

Getting started
- Fork the repository and create a feature branch: feature/<short-description>
- Keep commits small and focused. Use clear commit messages.

Development environment
- Use a Python virtual environment (venv or conda).
- Install dependencies: pip install -r requirements.txt
- Provide reproducible changes and update docs when behavior/config changes.

Code style
- Follow PEP8 for Python.
- Keep functions small and single-responsibility.
- Add docstrings for public functions and modules.

Tests
- Add unit tests for new behavior.
- Run tests locally before opening a PR.
- Include small sample images for deterministic test cases where appropriate.

Pull Requests
- Open a PR against the main branch with a clear description of what changed and why.
- Reference any related issues.
- Include screenshots or sample logs for behavioral changes (if relevant).
- Expect code review; address comments via new commits.

Security and data privacy
- Do not commit credentials, private images, or PII.
- Use environment variables or a secrets manager for DB/API credentials.
- When adding sample images, ensure they are synthetic/permissioned for public use.

License compatibility
- Ensure contributions and third-party libraries are compatible with the project license (see LICENSE).
