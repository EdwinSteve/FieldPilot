from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.identity.errors import InvalidSessionError
from app.identity.models import Principal, Role
from app.identity.tokens import JwtAccessTokens, new_refresh_token, refresh_token_hash

SECRET = "s" * 48
T0 = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


def _tokens() -> JwtAccessTokens:
    return JwtAccessTokens(SECRET, timedelta(minutes=15))


def test_a_token_round_trips_to_its_principal_until_it_expires() -> None:
    token = _tokens().issue(7, Role.CUSTOMER, T0)
    assert _tokens().principal(token, T0 + timedelta(minutes=14)) == Principal(7, Role.CUSTOMER)
    with pytest.raises(InvalidSessionError):
        _tokens().principal(token, T0 + timedelta(minutes=15))


def test_the_claims_carry_no_personal_data() -> None:
    token = _tokens().issue(7, Role.FARMER, T0)
    claims = jwt.decode(token, options={"verify_signature": False})
    assert set(claims) == {"sub", "role", "iss", "aud", "iat", "exp", "jti"}


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        jwt.encode({"sub": "7", "role": "admin"}, SECRET, algorithm="HS256"),  # claims missing
        JwtAccessTokens("o" * 48, timedelta(minutes=15)).issue(7, Role.ADMIN, T0),  # other key
    ],
)
def test_a_forged_or_incomplete_token_is_refused(token: str) -> None:
    with pytest.raises(InvalidSessionError):
        _tokens().principal(token, T0)


def test_an_unsigned_token_is_refused() -> None:
    claims = {"sub": "7", "role": "admin", "iss": "fieldpilot", "aud": "fieldpilot-api",
              "iat": 0, "exp": 2**40, "jti": "x"}  # fmt: skip
    with pytest.raises(InvalidSessionError):
        _tokens().principal(jwt.encode(claims, None, algorithm="none"), T0)


def test_a_short_key_is_refused() -> None:
    with pytest.raises(ValueError, match="at least"):
        JwtAccessTokens("short", timedelta(minutes=15))


def test_refresh_tokens_are_random_and_stored_as_a_digest() -> None:
    first, second = new_refresh_token(), new_refresh_token()
    assert first != second
    assert len(refresh_token_hash(first)) == 64
    assert refresh_token_hash(first) != first
