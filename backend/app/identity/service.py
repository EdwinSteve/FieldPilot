"""Register, login, refresh and logout (architecture §4.12, D082).

Time comes from the wall clock: the simulated farm clock can run faster and
must never expire a session.
"""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime, timedelta

from app.domain.errors import NotFoundError
from app.domain.models import JsonValue
from app.identity.config import IdentityConfig
from app.identity.errors import (
    AccountLockedError,
    ConsentRequiredError,
    ForbiddenError,
    InvalidCredentialsError,
    InvalidPhoneError,
    InvalidSessionError,
    PhoneTakenError,
    StalePolicyError,
)
from app.identity.models import (
    SELF_REGISTERED_ROLES,
    AuthEvent,
    AuthEventKind,
    AuthResult,
    Phone,
    Principal,
    RefreshSession,
    Registration,
    Role,
    TokenPair,
    User,
)
from app.identity.passwords import PasswordHasher, check_password
from app.identity.tokens import AccessTokens, new_refresh_token, refresh_token_hash
from app.persistence.ports import UnitOfWork
from app.simulator.clock import WallClock

UowFactory = Callable[[], UnitOfWork]
# Verified when the phone is unknown, so both failures take the same time (§4.12 rule 2).
_DUMMY_PASSWORD = "fieldpilot-timing-equaliser"


class AuthService:
    def __init__(
        self,
        uow: UowFactory,
        wall: WallClock,
        hasher: PasswordHasher,
        tokens: AccessTokens,
        config: IdentityConfig,
    ) -> None:
        self._uow = uow
        self._wall = wall
        self._hasher = hasher
        self._tokens = tokens
        self._config = config
        self._dummy_hash = hasher.hash(_DUMMY_PASSWORD)

    @property
    def privacy_policy_version(self) -> str:
        return self._config.privacy_policy_version

    def register(self, form: Registration) -> AuthResult:
        if form.role not in SELF_REGISTERED_ROLES:
            raise ForbiddenError("Only farmers and customers can register.", key="register_role")
        if not form.accept_privacy_policy:
            raise ConsentRequiredError(
                "You must accept the data processing policy.", key="consent_required"
            )
        if form.privacy_policy_version != self._config.privacy_policy_version:
            raise StalePolicyError(
                "The data policy changed. Read it again and accept it.", key="stale_policy"
            )
        now = self._wall()
        with self._uow() as uow:
            user = self._add_user(uow, form.phone, form.full_name, form.role, form.password, now)
            user_id = _stored_id(user)
            tokens = self._start_session(uow, user_id, user.role, now)
            uow.commit()
        return AuthResult(user, tokens)

    def create_account(
        self, phone: str, full_name: str, role: Role, password: str, plot_ids: Sequence[int] = ()
    ) -> User:
        """Server-side creation of any role, without a session (scripts/create_user.py).

        The person running the script attests that the user accepted the current policy.
        """
        now = self._wall()
        with self._uow() as uow:
            user = self._add_user(uow, phone, full_name, role, password, now)
            for plot_id in plot_ids:
                uow.plots.get(plot_id)
                uow.plot_members.add(plot_id, _stored_id(user))
            uow.commit()
        return user

    def login(self, phone: str, password: str) -> TokenPair:
        now = self._wall()
        try:
            parsed: Phone | None = Phone.parse(phone)
        except InvalidPhoneError:
            parsed = None
        with self._uow() as uow:
            user = None if parsed is None else uow.users.find_by_phone(parsed.e164)
            if user is None or not user.active:
                self._hasher.verify(password, self._dummy_hash)
                raise InvalidCredentialsError()
            user_id = _stored_id(user)
            if user.is_locked(now):
                self._hasher.verify(password, self._dummy_hash)
                raise AccountLockedError()
            if not self._hasher.verify(password, user.password_hash):
                self._record_failure(uow, user, now)
                uow.commit()
                raise InvalidCredentialsError()
            password_hash = user.password_hash
            if self._hasher.needs_rehash(password_hash):
                password_hash = self._hasher.hash(password)
            uow.users.update(
                replace(
                    user,
                    password_hash=password_hash,
                    failed_logins=0,
                    locked_until=None,
                    last_login_at=now,
                )
            )
            uow.auth_events.append(_event(AuthEventKind.LOGIN_SUCCEEDED, now, user_id))
            tokens = self._start_session(uow, user_id, user.role, now)
            uow.commit()
        return tokens

    def refresh(self, refresh_token: str) -> TokenPair:
        """Rotate the token. A token used twice revokes its whole family (§4.12 rule 5)."""
        now = self._wall()
        with self._uow() as uow:
            stored = uow.refresh_sessions.find_by_hash(refresh_token_hash(refresh_token))
            if stored is None or stored.id is None:
                raise InvalidSessionError()
            if stored.used_at is not None and stored.revoked_at is None:
                uow.refresh_sessions.revoke_family(stored.family_id, now)
                uow.auth_events.append(_event(AuthEventKind.REFRESH_REUSED, now, stored.user_id))
                uow.commit()
                raise InvalidSessionError()
            user = uow.users.get(stored.user_id)
            if not stored.is_usable(now) or not user.active:
                raise InvalidSessionError()
            uow.refresh_sessions.mark_used(stored.id, now)
            tokens = self._issue(uow, stored.user_id, user.role, stored.family_id, now)
            uow.auth_events.append(_event(AuthEventKind.SESSION_REFRESHED, now, stored.user_id))
            uow.commit()
        return tokens

    def logout(self, principal: Principal, refresh_token: str) -> None:
        """Revoke the session of this refresh token. Idempotent: 204 even if already revoked."""
        user_id = _authenticated(principal)
        now = self._wall()
        with self._uow() as uow:
            stored = uow.refresh_sessions.find_by_hash(refresh_token_hash(refresh_token))
            if stored is None or stored.user_id != user_id:
                return
            uow.refresh_sessions.revoke_family(stored.family_id, now)
            uow.auth_events.append(_event(AuthEventKind.LOGGED_OUT, now, user_id))
            uow.commit()

    def logout_all(self, principal: Principal) -> None:
        user_id = _authenticated(principal)
        now = self._wall()
        with self._uow() as uow:
            uow.refresh_sessions.revoke_user(user_id, now)
            uow.auth_events.append(_event(AuthEventKind.LOGGED_OUT_ALL, now, user_id))
            uow.commit()

    def me(self, principal: Principal) -> User:
        user_id = _authenticated(principal)
        with self._uow() as uow:
            return uow.users.get(user_id)

    def principal(self, access_token: str) -> Principal:
        """The caller of a request; the user must still exist and be active."""
        principal = self._tokens.principal(access_token, self._wall())
        try:
            with self._uow() as uow:
                user = uow.users.get(_authenticated(principal))
        except NotFoundError as error:
            raise InvalidSessionError() from error
        if not user.active or user.role is not principal.role:
            raise InvalidSessionError()
        return principal

    def _add_user(
        self, uow: UnitOfWork, raw_phone: str, full_name: str, role: Role, password: str,
        now: datetime,
    ) -> User:  # fmt: skip
        phone = Phone.parse(raw_phone)
        check_password(password, phone, self._config.password_min_length)
        if uow.users.find_by_phone(phone.e164) is not None:
            raise PhoneTakenError("An account with that phone already exists.", key="phone_taken")
        user = uow.users.add(
            User(
                phone=phone,
                full_name=full_name.strip(),
                role=role,
                password_hash=self._hasher.hash(password),
                consent_version=self._config.privacy_policy_version,
                consent_at=now,
                created_at=now,
            )
        )
        detail: dict[str, JsonValue] = {"role": role.value}
        uow.auth_events.append(_event(AuthEventKind.REGISTERED, now, _stored_id(user), detail))
        return user

    def _record_failure(self, uow: UnitOfWork, user: User, now: datetime) -> None:
        user_id = _stored_id(user)
        failures = user.failed_logins + 1
        locked = failures >= self._config.max_failed_logins
        until = now + timedelta(minutes=self._config.lockout_minutes) if locked else None
        uow.users.update(replace(user, failed_logins=0 if locked else failures, locked_until=until))
        uow.auth_events.append(_event(AuthEventKind.LOGIN_FAILED, now, user_id))
        if locked:
            uow.auth_events.append(_event(AuthEventKind.ACCOUNT_LOCKED, now, user_id))

    def _start_session(self, uow: UnitOfWork, user_id: int, role: Role, now: datetime) -> TokenPair:
        return self._issue(uow, user_id, role, uuid.uuid4().hex, now)

    def _issue(
        self, uow: UnitOfWork, user_id: int, role: Role, family_id: str, now: datetime
    ) -> TokenPair:
        refresh_token = new_refresh_token()
        uow.refresh_sessions.add(
            RefreshSession(
                user_id=user_id,
                token_hash=refresh_token_hash(refresh_token),
                family_id=family_id,
                expires_at=now + timedelta(days=self._config.refresh_token_days),
                created_at=now,
            )
        )
        access = self._tokens.issue(user_id, role, now)
        return TokenPair(access, refresh_token, int(self._tokens.lifetime.total_seconds()))


def _event(
    kind: AuthEventKind,
    at: datetime,
    user_id: int,
    detail: dict[str, JsonValue] | None = None,
) -> AuthEvent:
    return AuthEvent(kind=kind, occurred_at=at, user_id=user_id, detail=detail or {})


def _stored_id(user: User) -> int:
    if user.id is None:
        raise ValueError("user was not stored")
    return user.id


def _authenticated(principal: Principal) -> int:
    if principal.user_id is None:
        raise InvalidSessionError()
    return principal.user_id
