"""Encryption at rest for RoleIQ's SQLite columns.

Sensitive narrative text (resume, JD, analysis, interview history, ...) is
encrypted with Fernet (symmetric, authenticated) before it hits disk. The key
comes from RoleIQ_DB_KEY. If that env var is unset, a throwaway key is
generated for this process only -- data saved under it becomes unreadable the
moment RoleIQ restarts, so a loud warning is logged the first time that
happens rather than failing silently.

Short metadata columns (ids, role, company, timestamps) are NOT encrypted --
only the columns carrying resume/JD/analysis/history content go through this
module. See app.py's save_candidate/load_candidate/save_session.
"""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

_logger = logging.getLogger("roleiq")

_ephemeral_key: bytes | None = None
_warned_ephemeral = False


class DecryptionError(RuntimeError):
    """Raised when stored data cannot be decrypted with the configured key."""


def _generate_key_hint() -> str:
    return 'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'


def get_fernet() -> Fernet:
    global _ephemeral_key, _warned_ephemeral

    configured = (os.getenv("RoleIQ_DB_KEY") or "").strip()
    if configured:
        try:
            return Fernet(configured.encode("ascii"))
        except ValueError as e:
            raise DecryptionError(
                "RoleIQ_DB_KEY is not a valid Fernet key. Generate one with: "
                f"{_generate_key_hint()}"
            ) from e

    if _ephemeral_key is None:
        _ephemeral_key = Fernet.generate_key()
    if not _warned_ephemeral:
        _warned_ephemeral = True
        _logger.warning(
            "RoleIQ_DB_KEY is not set. Using a random, in-memory-only encryption "
            "key for this run. Data saved now will be UNREADABLE after RoleIQ "
            "restarts. Set RoleIQ_DB_KEY to persist encrypted data across runs. "
            "Generate one with: %s",
            _generate_key_hint(),
        )
    return Fernet(_ephemeral_key)


def encrypt_text(plain: str) -> str:
    if not plain:
        return ""
    return get_fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_text(token: str) -> str:
    if not token:
        return ""
    try:
        return get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise DecryptionError(
            "Stored data could not be decrypted -- RoleIQ_DB_KEY does not match "
            "the key used to encrypt this database, or the data is corrupted."
        ) from e
