"""Create an account on the server: the only way to create operators and admins (D082).

Run: make user PHONE=3001234567 NAME="Ana Pérez" ROLE=admin [PLOTS="1 2"]
The password is typed twice and never echoed, logged or passed on the command line.
"""

import argparse
import getpass
import secrets
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.errors import DomainError
from app.identity.config import load_identity_config
from app.identity.models import Role
from app.identity.passwords import Argon2Hasher
from app.identity.service import AuthService
from app.identity.tokens import JwtAccessTokens
from app.persistence.db import create_db_engine, init_schema
from app.persistence.ports import UnitOfWork
from app.persistence.unit_of_work import SqlUnitOfWork
from app.settings import Settings
from app.simulator.clock import system_wall_clock


def main() -> None:
    args = parse_args()
    settings = Settings()
    config = load_identity_config(settings.config_dir / "identity.yaml")
    answer = input(
        f"¿La persona aceptó la política de datos {config.privacy_policy_version}? [s/N] "
    )
    if answer.strip().lower() not in {"s", "si", "sí"}:
        print("Sin consentimiento no se crea la cuenta (Ley 1581 de 2012).")
        raise SystemExit(1)
    password = getpass.getpass("Contraseña: ")
    if getpass.getpass("Repite la contraseña: ") != password:
        print("Las contraseñas no coinciden.")
        raise SystemExit(1)
    engine = create_db_engine(settings.database_url)
    init_schema(engine)

    def uow() -> UnitOfWork:
        return SqlUnitOfWork(engine)

    # No token is issued here; the key only satisfies the constructor.
    tokens = JwtAccessTokens(secrets.token_urlsafe(48), timedelta(minutes=1))
    service = AuthService(uow, system_wall_clock, Argon2Hasher(), tokens, config)
    try:
        user = service.create_account(args.phone, args.name, Role(args.role), password, args.plot)
    except DomainError as error:
        print(error)
        raise SystemExit(1) from error
    print(f"Cuenta {user.id} creada: {user.role.value}, parcelas {args.plot or 'ninguna'}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an account of any role.")
    parser.add_argument("--phone", required=True, help="Colombian mobile, e.g. 3001234567")
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", required=True, choices=[r.value for r in Role])
    parser.add_argument("--plot", type=int, action="append", default=[], help="repeatable")
    return parser.parse_args()


if __name__ == "__main__":
    main()
