"""Access tokens (JWT, HS256) and opaque refresh tokens (§4.12 rules 4 and 5)."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Protocol

import jwt

from app.identity.errors import InvalidSessionError
from app.identity.models import Principal, Role

ISSUER = "fieldpilot"
AUDIENCE = "fieldpilot-api"
ALGORITHM = "HS256"
REFRESH_TOKEN_BYTES = 32
MIN_SECRET_LENGTH = 32


class AccessTokens(Protocol):
    @property
    def lifetime(self) -> timedelta: ...
    def issue(self, user_id: int, role: Role, now: datetime) -> str: ...
    def principal(self, token: str, now: datetime) -> Principal: ...


class JwtAccessTokens:
    """Claims are identifiers only: a JWT can be read by anyone who holds it."""

    def __init__(self, secret: str, lifetime: timedelta) -> None:
        if len(secret) < MIN_SECRET_LENGTH:
            raise ValueError(f"the signing key needs at least {MIN_SECRET_LENGTH} characters")
        self._secret = secret
        self._lifetime = lifetime

    @property
    def lifetime(self) -> timedelta:
        return self._lifetime

    def issue(self, user_id: int, role: Role, now: datetime) -> str:
        claims = {
            "sub": str(user_id),
            "role": role.value,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + self._lifetime).timestamp()),
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(claims, self._secret, algorithm=ALGORITHM)

    def principal(self, token: str, now: datetime) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                audience=AUDIENCE,
                issuer=ISSUER,
                # Times are checked below against the injected clock, not PyJWT's own.
                options={"require": ["sub", "role", "iss", "aud", "iat", "exp", "jti"],
                         "verify_exp": False, "verify_iat": False},
            )  # fmt: skip
            expires = int(claims["exp"])
            principal = Principal(int(claims["sub"]), Role(claims["role"]))
        except (jwt.PyJWTError, ValueError, KeyError) as error:
            raise InvalidSessionError() from error
        if expires <= now.timestamp():
            raise InvalidSessionError()
        return principal


def new_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def refresh_token_hash(token: str) -> str:
    """Only this digest is stored: a leaked table cannot open a session."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
