"""The autonomy policy the gate enforces: read-only (D073)."""

from fastapi import APIRouter

from app.api.deps import ContainerDep
from app.api.schemas import PolicyOut

router = APIRouter(prefix="/autonomy", tags=["autonomy"])


@router.get("/policy")
def get_policy(container: ContainerDep) -> PolicyOut:
    return PolicyOut.of(container.config.policy)
