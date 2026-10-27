"""Liveness endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API process is up."""
    return HealthResponse(status="ok")
