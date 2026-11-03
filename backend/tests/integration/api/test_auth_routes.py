"""Login, register and sessions with AUTH_REQUIRED on, as in production (§4.12, D082)."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.container import Container
from app.domain.errors import ConfigError
from app.domain.models import Plot
from app.identity.models import AuthEventKind, Role
from app.main import create_app
from app.settings import Settings

SECRET = "k" * 48
PASSWORD = "cafe-con-panela"
FARMER_PHONE = "3001234567"
T0 = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class Secured:
    client: TestClient
    container: Container
    plot_id: int
    policy: str


@pytest.fixture
def secured(tmp_path: Path) -> Iterator[Secured]:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'auth.db'}",
        mock_llm=True,
        auth_jwt_secret=SECRET,
        planner_site_builder="off",
    )
    app = create_app(settings)
    container: Container = app.state.container
    with container.runtime.uow() as uow:
        plot = uow.plots.add(Plot("Neiva", 2.93, -75.28, 2.0, T0, utc_offset_hours=-5.0))
        uow.commit()
    assert plot.id is not None
    with TestClient(app) as client:
        policy = client.get("/auth/privacy-policy").json()["version"]
        yield Secured(client, container, plot.id, policy)


def _register(s: Secured, phone: str = FARMER_PHONE, role: str = "farmer", **extra: Any) -> Any:
    body = {
        "phone": phone,
        "full_name": "Ana Pérez",
        "password": PASSWORD,
        "role": role,
        "accept_privacy_policy": True,
        "privacy_policy_version": s.policy,
    } | extra
    return s.client.post("/auth/register", json=body)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _farmer(s: Secured) -> dict[str, Any]:
    response = _register(s)
    assert response.status_code == 201, response.json()
    body: dict[str, Any] = response.json()
    return body


def _admin(s: Secured) -> str:
    """Admins are created on the server (scripts/create_user.py), never through the API."""
    s.container.auth.create_account("3109998877", "Admin", Role.ADMIN, PASSWORD)
    response = s.client.post("/auth/login", json={"phone": "3109998877", "password": PASSWORD})
    token: str = response.json()["access_token"]
    return token


def test_register_logs_in_and_records_consent(secured: Secured) -> None:
    body = _farmer(secured)

    assert body["user"]["phone"] == "+573001234567"
    assert body["user"]["role"] == "farmer"
    assert body["tokens"]["token_type"] == "bearer"
    me = secured.client.get("/auth/me", headers=_bearer(body["tokens"]["access_token"]))
    assert me.json() == body["user"]
    assert "password" not in str(me.json())
    with secured.container.runtime.uow() as uow:
        user = uow.users.get(body["user"]["id"])
        events = uow.auth_events.list(user.id)
    assert user.password_hash.startswith("$argon2id$")
    assert user.consent_version == secured.policy
    assert [e.kind for e in events] == [AuthEventKind.REGISTERED]


@pytest.mark.parametrize(
    ("extra", "status"),
    [
        ({"accept_privacy_policy": False}, 422),
        ({"privacy_policy_version": "2020-01-01"}, 409),
        ({"role": "admin"}, 422),
        ({"password": "corta"}, 422),
        ({"password": "clave3001234567"}, 422),
        ({"phone": "6012345678"}, 422),
    ],
)
def test_register_refuses_what_breaks_a_rule(
    secured: Secured, extra: dict[str, Any], status: int
) -> None:
    assert _register(secured, **extra).status_code == status


def test_a_phone_registers_once(secured: Secured) -> None:
    _farmer(secured)
    assert _register(secured, phone="+57 300 123 4567").status_code == 409


def test_unknown_phone_and_wrong_password_get_the_same_answer(secured: Secured) -> None:
    _farmer(secured)
    unknown = secured.client.post("/auth/login", json={"phone": "3110000000", "password": "x"})
    wrong = secured.client.post("/auth/login", json={"phone": FARMER_PHONE, "password": "x"})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()
    assert unknown.headers["WWW-Authenticate"] == "Bearer"


def test_five_failures_lock_the_account_even_for_the_right_password(secured: Secured) -> None:
    _farmer(secured)
    for _ in range(5):
        secured.client.post("/auth/login", json={"phone": FARMER_PHONE, "password": "nope"})

    right = secured.client.post("/auth/login", json={"phone": FARMER_PHONE, "password": PASSWORD})

    assert right.status_code == 423
    with secured.container.runtime.uow() as uow:
        events = uow.auth_events.list()
    kinds = [e.kind for e in events]
    assert kinds.count(AuthEventKind.LOGIN_FAILED) == 5
    assert AuthEventKind.ACCOUNT_LOCKED in kinds
    assert "300" not in str([e.detail for e in events])  # no phone in the audit log


def test_refresh_rotates_and_a_reused_token_ends_the_family(secured: Secured) -> None:
    first = _farmer(secured)["tokens"]["refresh_token"]

    rotated = secured.client.post("/auth/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200
    second = rotated.json()["refresh_token"]
    assert second != first

    replay = secured.client.post("/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401
    # The thief's replay also closed the session the real user was holding.
    assert secured.client.post("/auth/refresh", json={"refresh_token": second}).status_code == 401


def test_logout_closes_the_session_and_logout_all_closes_every_one(secured: Secured) -> None:
    tokens = _farmer(secured)["tokens"]
    other = secured.client.post("/auth/login", json={"phone": FARMER_PHONE, "password": PASSWORD})
    headers = _bearer(tokens["access_token"])

    out = secured.client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers
    )
    assert out.status_code == 204
    refreshed = {"refresh_token": tokens["refresh_token"]}
    assert secured.client.post("/auth/refresh", json=refreshed).status_code == 401

    assert secured.client.post("/auth/logout-all", headers=headers).status_code == 204
    still = {"refresh_token": other.json()["refresh_token"]}
    assert secured.client.post("/auth/refresh", json=still).status_code == 401


def test_farm_routes_need_a_token_and_a_farm_role(secured: Secured) -> None:
    assert secured.client.get("/tasks").status_code == 401
    bad = secured.client.get("/tasks", headers=_bearer("garbage"))
    assert bad.status_code == 401

    customer = _register(secured, phone="3157654321", role="customer").json()
    forbidden = secured.client.get("/tasks", headers=_bearer(customer["tokens"]["access_token"]))
    assert forbidden.status_code == 403

    farmer = _farmer(secured)["tokens"]["access_token"]
    assert secured.client.get("/tasks", headers=_bearer(farmer)).status_code == 200
    assert secured.client.get("/health").status_code == 200  # stays public


def test_a_plot_needs_membership_given_by_an_admin(secured: Secured) -> None:
    farmer = _farmer(secured)
    token, user_id = farmer["tokens"]["access_token"], farmer["user"]["id"]
    zones = f"/plots/{secured.plot_id}/zones"
    assert secured.client.get(zones, headers=_bearer(token)).status_code == 403

    members = f"/plots/{secured.plot_id}/members"
    self_grant = secured.client.post(members, json={"user_id": user_id}, headers=_bearer(token))
    assert self_grant.status_code == 403
    admin = _admin(secured)
    granted = secured.client.post(members, json={"user_id": user_id}, headers=_bearer(admin))
    assert granted.status_code == 204

    assert secured.client.get(zones, headers=_bearer(token)).status_code == 200
    assert secured.client.get("/plots/999/zones", headers=_bearer(token)).status_code == 404


def test_an_account_created_on_the_server_can_be_given_plots(secured: Secured) -> None:
    user = secured.container.auth.create_account(
        "3201112233", "Operaria", Role.OPERATOR, PASSWORD, [secured.plot_id]
    )

    assert user.id is not None
    with secured.container.runtime.uow() as uow:
        assert uow.plot_members.is_member(secured.plot_id, user.id)
    login = {"phone": "3201112233", "password": PASSWORD}
    token = secured.client.post("/auth/login", json=login).json()["access_token"]
    # An operator is not a farm role, membership or not (D080 gives operators the warehouse).
    assert secured.client.get("/tasks", headers=_bearer(token)).status_code == 403


def test_farm_events_name_the_real_user(secured: Secured) -> None:
    farmer = _farmer(secured)
    headers = _bearer(farmer["tokens"]["access_token"])

    stop = secured.client.post("/emergency-stop", json={"active": True}, headers=headers)

    assert stop.json()["changed_by"] == f"farmer:{farmer['user']['id']}"


def _settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, database_url="sqlite://", mock_llm=True, **overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"auth_required": False},  # only the demo profile may turn auth off
        {"auth_required": False, "app_profile": "prod", "auth_jwt_secret": SECRET},
        {"app_profile": "prod"},  # prod needs a configured key
        {"auth_jwt_secret": "short"},
    ],
)
def test_an_unsafe_auth_setting_stops_the_app(overrides: dict[str, Any]) -> None:
    with pytest.raises(ConfigError):
        create_app(_settings(**overrides))


def test_the_demo_profile_may_run_without_tokens() -> None:
    app = create_app(_settings(app_profile="demo", auth_required=False))
    with TestClient(app) as client:
        assert client.get("/tasks").status_code == 200


def test_a_farmer_sees_only_the_plots_they_created_or_were_given(secured: Secured) -> None:
    ana = _farmer(secured)["tokens"]["access_token"]
    luis = _register(secured, phone="3112223344").json()["tokens"]["access_token"]
    plot = {"name": "La Esperanza", "municipality": "La Plata", "department": "Huila",
            "latitude": 2.39, "longitude": -75.89, "area_ha": 3.5}  # fmt: skip

    created = secured.client.post("/plots", json=plot, headers=_bearer(ana)).json()

    assert [p["id"] for p in secured.client.get("/plots", headers=_bearer(ana)).json()] == [
        created["id"]
    ]
    assert secured.client.get("/plots", headers=_bearer(luis)).json() == []
    site = f"/plots/{created['id']}/site"
    assert secured.client.get(site, headers=_bearer(luis)).status_code == 403


def test_the_passport_is_public(secured: Secured) -> None:
    assert secured.client.get("/trace/FP-1-20261028-1").status_code == 404  # not 401
