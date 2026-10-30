"""The event log, notifications and reports: what happened, and what the farmer was told."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ContainerDep
from app.api.schemas import EventOut, NotificationOut, ReportOut
from app.domain.enums import EventKind

router = APIRouter(tags=["log"])


@router.get("/events")
def list_events(
    container: ContainerDep,
    task_id: int | None = None,
    kind: EventKind | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> list[EventOut]:
    """Oldest first; the agent trace is `kind=agent_tool_call` (D045)."""
    return [EventOut.of(e) for e in container.queries.events(task_id, kind, limit)]


@router.get("/notifications")
def list_notifications(container: ContainerDep, unread_only: bool = False) -> list[NotificationOut]:
    return [NotificationOut.of(n) for n in container.queries.notifications(unread_only)]


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, container: ContainerDep) -> NotificationOut:
    return NotificationOut.of(container.queries.mark_read(notification_id))


@router.get("/reports")
def list_reports(container: ContainerDep) -> list[ReportOut]:
    return [ReportOut.of(r) for r in container.queries.reports()]
