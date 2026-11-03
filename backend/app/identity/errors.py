"""Identity errors. Messages are shown to the person, so they are in Spanish."""

from app.domain.errors import DomainError


class InvalidPhoneError(DomainError):
    """The phone is not a Colombian mobile number."""


class WeakPasswordError(DomainError):
    """The password breaks the policy in config/identity.yaml."""


class ConsentRequiredError(DomainError):
    """Registration without accepting the privacy policy."""


class StalePolicyError(DomainError):
    """The privacy policy version accepted is not the current one."""


class PhoneTakenError(DomainError):
    """Another account already uses this phone."""


class InvalidCredentialsError(DomainError):
    """Unknown phone or wrong password: one message for both (§4.12 rule 2)."""

    def __init__(self) -> None:
        super().__init__("El celular o la contraseña no son correctos.")


class AccountLockedError(DomainError):
    """Too many failed logins in a row (§4.12 rule 3)."""

    def __init__(self) -> None:
        super().__init__("La cuenta está bloqueada por intentos fallidos. Intenta más tarde.")


class InvalidSessionError(DomainError):
    """A missing, expired, revoked or forged token."""

    def __init__(self) -> None:
        super().__init__("La sesión no es válida. Inicia sesión de nuevo.")


class ForbiddenError(DomainError):
    """The caller is authenticated but may not do this."""
