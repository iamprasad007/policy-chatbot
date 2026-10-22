from cryptography.fernet import Fernet

from app.core.config import get_settings

settings = get_settings()
_fernet = Fernet(settings.encryption_key.encode())


def encrypt_secret(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()


def mask_secret(plain: str) -> str:
    if len(plain) <= 4:
        return "*" * len(plain)
    return f"{'*' * (len(plain) - 4)}{plain[-4:]}"
