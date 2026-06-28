"""
VigyanLLM Data Encryption Module
===================================
Fernet (AES-256-CBC + HMAC-SHA256) symmetric encryption for pipeline result data at rest.

Key derivation order:
  1. DATA_ENCRYPTION_KEY env var (recommended — persistent across restarts)
  2. PRIMERFORGE_SECRET env var  (fallback — already required for sessions)
  3. Auto-generated random key  (last resort — ephemeral, data lost on restart)

Encryption is applied server-side only. The key never leaves the server.
"""

import os
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("primerforge.crypto")

_KEY_CACHE = None


def _get_key() -> bytes:
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE

    raw = os.environ.get("DATA_ENCRYPTION_KEY")
    if raw:
        try:
            _KEY_CACHE = raw.encode("ascii") if isinstance(raw, str) else raw
            Fernet(_KEY_CACHE)
            logger.info("DATA_ENCRYPTION_KEY loaded from environment")
            return _KEY_CACHE
        except Exception:
            logger.warning("Invalid DATA_ENCRYPTION_KEY format — falling back")

    secret = os.environ.get("PRIMERFORGE_SECRET")
    if secret:
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        _KEY_CACHE = base64.urlsafe_b64encode(digest)
        logger.info("DATA_ENCRYPTION_KEY derived from PRIMERFORGE_SECRET (SHA-256)")
        return _KEY_CACHE

    import secrets as _secrets
    _KEY_CACHE = Fernet.generate_key()
    logger.warning(
        "No DATA_ENCRYPTION_KEY or PRIMERFORGE_SECRET set — "
        "using ephemeral encryption key. Encrypted data will be "
        "unreadable after server restart. Set DATA_ENCRYPTION_KEY "
        "in your .env file for persistence."
    )
    return _KEY_CACHE


def encrypt_data(plain_text: str) -> str:
    if not plain_text:
        return ""
    key = _get_key()
    cipher = Fernet(key)
    return cipher.encrypt(plain_text.encode("utf-8")).decode("ascii")


def decrypt_data(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    key = _get_key()
    cipher = Fernet(key)
    try:
        return cipher.decrypt(cipher_text.encode("ascii")).decode("utf-8")
    except (InvalidToken, Exception) as e:
        logger.error("Data decryption failed: %s", e)
        return ""
