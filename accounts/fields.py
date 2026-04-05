from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet


class EncryptedTextField(models.TextField):
    """DB保存時に自動暗号化、読み出し時に自動復号するカスタムフィールド"""

    def _get_fernet(self):
        key = settings.ENCRYPTION_KEY
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self._get_fernet().decrypt(value.encode()).decode()

    def get_prep_value(self, value):
        if value is None:
            return value
        return self._get_fernet().encrypt(value.encode()).decode()
