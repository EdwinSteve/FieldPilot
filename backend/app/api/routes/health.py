"""Liveness endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import ContainerDep

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str
    mock_llm: bool


@router.get("/health", response_model=HealthResponse)
def health(container: ContainerDep) -> HealthResponse:
    """Report that the API process is up, and whether the chat is off (D063, D072)."""
    return HealthResponse(status="ok", mock_llm=container.mock_llm)
