"""Register, login, sessions, the privacy policy and plot members (§4.12, D082)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import PrincipalDep
from app.api.deps import ContainerDep
from app.identity.config import MAX_PASSWORD_LENGTH
from app.identity.models import Registration, Role, TokenPair, User

router = APIRouter(tags=["auth"])

Password = Annotated[str, Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RegisterIn(_In):
    phone: Annotated[str, Field(min_length=10, max_length=20)]
    full_name: Annotated[str, Field(min_length=2, max_length=120)]
    password: Password
    role: Literal["farmer", "customer"]
    accept_privacy_policy: bool
    privacy_policy_version: Annotated[str, Field(min_length=1, max_length=40)]


class LoginIn(_In):
    phone: Annotated[str, Field(min_length=1, max_length=20)]
    password: Password


class RefreshIn(_In):
    refresh_token: Annotated[str, Field(min_length=1, max_length=200)]


class MemberIn(_In):
    user_id: int


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

    @classmethod
    def of(cls, pair: TokenPair) -> "TokenOut":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_in=pair.expires_in,
        )


class UserOut(BaseModel):
    """The account as its owner sees it; never the password hash or the lockout state."""

    id: int
    phone: str
    full_name: str
    role: Role

    @classmethod
    def of(cls, user: User) -> "UserOut":
        if user.id is None:
            raise ValueError("user was not stored")
        return cls(id=user.id, phone=user.phone.e164, full_name=user.full_name, role=user.role)


class RegisterOut(BaseModel):
    user: UserOut
    tokens: TokenOut


class PrivacyPolicyOut(BaseModel):
    version: str


@router.get("/auth/privacy-policy")
def privacy_policy(container: ContainerDep) -> PrivacyPolicyOut:
    """The version the register form must send back as accepted."""
    return PrivacyPolicyOut(version=container.auth.privacy_policy_version)


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, container: ContainerDep) -> RegisterOut:
    result = container.auth.register(
        Registration(
            phone=body.phone,
            full_name=body.full_name,
            password=body.password,
            role=Role(body.role),
            accept_privacy_policy=body.accept_privacy_policy,
            privacy_policy_version=body.privacy_policy_version,
        )
    )
    return RegisterOut(user=UserOut.of(result.user), tokens=TokenOut.of(result.tokens))


@router.post("/auth/login")
def login(body: LoginIn, container: ContainerDep) -> TokenOut:
    return TokenOut.of(container.auth.login(body.phone, body.password))


@router.post("/auth/refresh")
def refresh(body: RefreshIn, container: ContainerDep) -> TokenOut:
    return TokenOut.of(container.auth.refresh(body.refresh_token))


@router.post("/auth/logout", status_code=204)
def logout(body: RefreshIn, principal: PrincipalDep, container: ContainerDep) -> Response:
    container.auth.logout(principal, body.refresh_token)
    return Response(status_code=204)


@router.post("/auth/logout-all", status_code=204)
def logout_all(principal: PrincipalDep, container: ContainerDep) -> Response:
    container.auth.logout_all(principal)
    return Response(status_code=204)


@router.get("/auth/me")
def me(principal: PrincipalDep, container: ContainerDep) -> UserOut:
    return UserOut.of(container.auth.me(principal))


@router.post("/plots/{plot_id}/members", status_code=204)
def add_member(
    plot_id: int, body: MemberIn, principal: PrincipalDep, container: ContainerDep
) -> Response:
    """Admin only: give a user access to a plot."""
    container.access.add_member(principal, plot_id, body.user_id)
    return Response(status_code=204)
