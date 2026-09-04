"""Pure security helpers with no database/runtime dependencies."""

import hashlib


def hash_api_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def api_key_prefix(token: str) -> str | None:
    # Device keys are generated as scs_<12-char-prefix>_<secret>.
    parts = token.split("_", 2)
    if len(parts) != 3 or parts[0] != "scs" or not parts[1]:
        return None
    return parts[1]
