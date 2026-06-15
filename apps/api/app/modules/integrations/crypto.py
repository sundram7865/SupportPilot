from cryptography.fernet import Fernet

from app.core.config import get_settings


def get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.integration_secret_key.encode())


def encrypt_secret(secret: str) -> str:
    fernet = get_fernet()
    return fernet.encrypt(secret.encode()).decode()


def decrypt_secret(encrypted_secret: str) -> str:
    fernet = get_fernet()
    return fernet.decrypt(encrypted_secret.encode()).decode()