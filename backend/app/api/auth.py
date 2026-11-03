"""Who is calling, and what they may reach (architecture §4.12, D082).

Routes declare these as dependencies; FastAPI resolves the principal once
per request and shares it with every dependency that asks for it.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import ContainerDep
from app.identity.errors import InvalidSessionError
from app.identity.models import Principal

_bearer = HTTPBearer(auto_error=False)
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def current_principal(container: ContainerDep, credentials: BearerDep) -> Principal:
    """The token's user. Without a token, the demo farmer when AUTH_REQUIRED=0, else 401."""
    if credentials is not None:
        return container.auth.principal(credentials.credentials)
    if not container.auth_required:
        return Principal.demo_farmer()
    raise InvalidSessionError()


PrincipalDep = Annotated[Principal, Depends(current_principal)]


def require_farm_access(
    request: Request, principal: PrincipalDep, container: ContainerDep
) -> Principal:
    """Farm routes: a farm role, and membership of any plot named in the path or query."""
    raw = request.path_params.get("plot_id") or request.query_params.get("plot_id")
    plot_id = int(raw) if raw is not None and str(raw).isdigit() else None
    container.access.require_farm(principal, plot_id)
    return principal


FarmerDep = Annotated[Principal, Depends(require_farm_access)]
