"""Password hashing (Argon2id) and the password policy (§4.12 rule 1)."""

from typing import Protocol

from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.identity.config import MAX_PASSWORD_LENGTH
from app.identity.errors import WeakPasswordError
from app.identity.models import Phone


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, encoded: str) -> bool: ...
    def needs_rehash(self, encoded: str) -> bool: ...


class Argon2Hasher:
    """Argon2id with argon2-cffi's defaults (RFC 9106, low-memory profile)."""

    def __init__(self) -> None:
        self._argon2 = _Argon2()

    def hash(self, password: str) -> str:
        return self._argon2.hash(password)

    def verify(self, password: str, encoded: str) -> bool:
        try:
            return self._argon2.verify(encoded, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, encoded: str) -> bool:
        return self._argon2.check_needs_rehash(encoded)


def check_password(password: str, phone: Phone, min_length: int) -> None:
    """Length within bounds, and the phone number is not part of it."""
    if not min_length <= len(password) <= MAX_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"La contraseña debe tener entre {min_length} y {MAX_PASSWORD_LENGTH} caracteres."
        )
    if phone.national in password:
        raise WeakPasswordError("La contraseña no puede contener el número de celular.")
