"""Identity value objects and entities. Every datetime is aware UTC, from the wall clock."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.models import JsonValue
from app.identity.errors import InvalidPhoneError


class Role(StrEnum):
    FARMER = "farmer"
    CUSTOMER = "customer"
    OPERATOR = "operator"  # warehouse operator (D080)
    ADMIN = "admin"


SELF_REGISTERED_ROLES = frozenset({Role.FARMER, Role.CUSTOMER})
FARM_ROLES = frozenset({Role.FARMER, Role.ADMIN})

# A Colombian mobile: 10 digits starting with 3, with or without +57.
_MOBILE = re.compile(r"^(?:\+?57)?(3\d{9})$")


@dataclass(frozen=True)
class Phone:
    """A Colombian mobile number in E.164 form, e.g. +573001234567."""

    e164: str

    @classmethod
    def parse(cls, raw: str) -> "Phone":
        digits = re.sub(r"[\s\-().]", "", raw)
        match = _MOBILE.fullmatch(digits)
        if match is None:
            raise InvalidPhoneError(
                "The phone must be a 10-digit Colombian mobile number.", key="invalid_phone"
            )
        return cls(f"+57{match.group(1)}")

    @property
    def national(self) -> str:
        """The 10 digits, without +57."""
        return self.e164[3:]


@dataclass(frozen=True)
class User:
    phone: Phone
    full_name: str
    role: Role
    password_hash: str
    consent_version: str  # the privacy policy accepted (Ley 1581 de 2012)
    consent_at: datetime
    created_at: datetime
    active: bool = True
    failed_logins: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    id: int | None = None

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > now


@dataclass(frozen=True)
class Principal:
    """Who is calling: from a verified access token, or the demo farmer (AUTH_REQUIRED=0)."""

    user_id: int | None
    role: Role

    @classmethod
    def demo_farmer(cls) -> "Principal":
        return cls(None, Role.FARMER)

    @property
    def actor(self) -> str:
        """The actor written to farm events (principle 6)."""
        suffix = "dashboard" if self.user_id is None else str(self.user_id)
        return f"{self.role.value}:{suffix}"

    @property
    def sees_every_plot(self) -> bool:
        """Admins, and the demo farmer of a single-farm demo, skip the plot membership check."""
        return self.role is Role.ADMIN or self.user_id is None


@dataclass(frozen=True)
class RefreshSession:
    """One refresh token, stored only as its SHA-256. A family is one login's chain."""

    user_id: int
    token_hash: str
    family_id: str
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    id: int | None = None

    def is_usable(self, now: datetime) -> bool:
        return self.used_at is None and self.revoked_at is None and self.expires_at > now


class AuthEventKind(StrEnum):
    REGISTERED = "registered"
    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_FAILED = "login_failed"
    ACCOUNT_LOCKED = "account_locked"
    SESSION_REFRESHED = "session_refreshed"
    REFRESH_REUSED = "refresh_reused"
    LOGGED_OUT = "logged_out"
    LOGGED_OUT_ALL = "logged_out_all"


@dataclass(frozen=True)
class AuthEvent:
    """Security audit entry. Never holds a phone, a password or a token."""

    kind: AuthEventKind
    occurred_at: datetime
    user_id: int | None = None
    detail: Mapping[str, JsonValue] = field(default_factory=dict)
    id: int | None = None


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int  # seconds until the access token expires


@dataclass(frozen=True)
class Registration:
    phone: str
    full_name: str
    password: str
    role: Role
    accept_privacy_policy: bool
    privacy_policy_version: str


@dataclass(frozen=True)
class AuthResult:
    user: User
    tokens: TokenPair
