"""Liveness endpoint, and what is answering: the live model or a labeled replay."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import ContainerDep

router = APIRouter(tags=["health"])


class ReplayOut(BaseModel):
    """The recorded run the daily cycle replays under MOCK_LLM=1 (D063, D076)."""

    recorded_on: str | None
    model: str | None


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str
    mock_llm: bool
    # D094: shown by the UI as a permanent badge, so a replay is never taken for a live run.
    llm_mode: Literal["live", "replay"]
    agent_model: str | None  # the Muse model the agents call live; None in replay
    replay: ReplayOut | None  # what is replayed; None live
    daily_cycle: str  # "orchestrated" (D093) or "pipeline"
    agents: list[str]  # the farm's agents, the agronomist first


@router.get("/health", response_model=HealthResponse)
def health(container: ContainerDep) -> HealthResponse:
    """Report that the API process is up, and whether the model is live (D063, D072, D094)."""
    replay = container.replay
    return HealthResponse(
        status="ok",
        mock_llm=container.mock_llm,
        llm_mode="replay" if container.mock_llm else "live",
        agent_model=None if container.mock_llm else container.agent_model,
        replay=None if replay is None else ReplayOut(**replay),
        daily_cycle=container.daily_cycle_kind,
        agents=sorted(
            (a.name for a in container.config.subagents),
            key=lambda name: (name != "agronomist", name),
        ),
    )
