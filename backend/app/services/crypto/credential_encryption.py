"""
Overview: Fernet symmetric encryption for cloud backend credentials. Encrypts/decrypts
    credential dictionaries stored as BYTEA in the database.
Architecture: Crypto utility layer — called by CloudBackendService (Section 11)
Dependencies: cryptography.fernet, os, json
Concepts: Fernet provides AES-128-CBC + HMAC-SHA256. The encryption key is loaded from
    the NIMBUS_CREDENTIAL_KEY environment variable. Credentials are write-only in the API;
    only hasCredentials (bool) is exposed.
"""

from __future__ import annotations

import json
import os

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptionError(Exception):
    """Raised when encryption or decryption fails."""


def _get_fernet() -> Fernet:
    """Retrieve the Fernet instance, using the NIMBUS_CREDENTIAL_KEY env var."""
    key = os.environ.get("NIMBUS_CREDENTIAL_KEY")
    if not key:
        raise CredentialEncryptionError(
            "NIMBUS_CREDENTIAL_KEY environment variable is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise CredentialEncryptionError(f"Invalid NIMBUS_CREDENTIAL_KEY: {exc}") from exc


def encrypt_credentials(credentials: dict) -> bytes:
    """Encrypt a credentials dictionary into Fernet-encrypted bytes."""
    f = _get_fernet()
    payload = json.dumps(credentials, separators=(",", ":")).encode("utf-8")
    return f.encrypt(payload)


def decrypt_credentials(encrypted: bytes) -> dict:
    """Decrypt Fernet-encrypted bytes back into a credentials dictionary."""
    f = _get_fernet()
    try:
        payload = f.decrypt(encrypted)
        return json.loads(payload)
    except InvalidToken as exc:
        raise CredentialEncryptionError(
            "Failed to decrypt credentials — key may have changed"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CredentialEncryptionError(
            "Decrypted payload is not valid JSON"
        ) from exc


def generate_key() -> str:
    """Generate a new Fernet key (for initial setup)."""
    return Fernet.generate_key().decode()
