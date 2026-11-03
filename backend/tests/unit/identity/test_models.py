from datetime import UTC, datetime, timedelta

import pytest

from app.identity.errors import InvalidPhoneError, WeakPasswordError
from app.identity.models import Phone, Principal, Role
from app.identity.passwords import Argon2Hasher, check_password

T0 = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "raw", ["3001234567", "+573001234567", "573001234567", "300 123 4567", "(300) 123-4567"]
)
def test_a_colombian_mobile_is_stored_in_e164(raw: str) -> None:
    assert Phone.parse(raw).e164 == "+573001234567"


@pytest.mark.parametrize("raw", ["", "6012345678", "30012345", "+13001234567", "300123456789"])
def test_anything_else_is_refused(raw: str) -> None:
    with pytest.raises(InvalidPhoneError):
        Phone.parse(raw)


def test_a_password_must_respect_the_length_and_leave_out_the_phone() -> None:
    phone = Phone.parse("3001234567")
    check_password("cafe-con-panela", phone, 10)
    with pytest.raises(WeakPasswordError):
        check_password("corta", phone, 10)
    with pytest.raises(WeakPasswordError):
        check_password("x" * 129, phone, 10)
    with pytest.raises(WeakPasswordError):
        check_password("mi3001234567clave", phone, 10)


def test_argon2_verifies_only_the_right_password() -> None:
    hasher = Argon2Hasher()
    encoded = hasher.hash("cafe-con-panela")
    assert encoded.startswith("$argon2id$")
    assert hasher.verify("cafe-con-panela", encoded)
    assert not hasher.verify("cafe-con-leche", encoded)
    assert not hasher.verify("cafe-con-panela", "not-a-hash")


def test_the_actor_names_the_user_or_the_demo_dashboard() -> None:
    assert Principal(12, Role.FARMER).actor == "farmer:12"
    assert Principal.demo_farmer().actor == "farmer:dashboard"
    assert Principal.demo_farmer().sees_every_plot
    assert Principal(1, Role.ADMIN).sees_every_plot
    assert not Principal(12, Role.FARMER).sees_every_plot


def test_a_lock_lasts_until_its_time() -> None:
    from app.identity.models import User  # noqa: PLC0415 - keeps the import next to its use

    user = User(
        Phone.parse("3001234567"), "Ana", Role.FARMER, "h", "v1", T0, T0,
        locked_until=T0 + timedelta(minutes=15),
    )  # fmt: skip
    assert user.is_locked(T0)
    assert not user.is_locked(T0 + timedelta(minutes=15))
