import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY")


def _get_fernet() -> Optional[Fernet]:
    if not TOKEN_ENCRYPTION_KEY:
        return None
    return Fernet(TOKEN_ENCRYPTION_KEY.encode())


def encrypt_token(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    f = _get_fernet()
    if not f:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set")
    return f.encrypt(value.encode()).decode()


def decrypt_token(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    f = _get_fernet()
    if not f:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set")
    try:
        return f.decrypt(value.encode()).decode()
    except InvalidToken:
        raise RuntimeError("Invalid token encryption key or corrupted data")
