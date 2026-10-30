"""Tasks and the farmer's decisions on them (D008, D011, D062)."""

from fastapi import APIRouter

from app.api.deps import FARMER, ContainerDep
from app.api.schemas import RejectIn, RevertOut, TaskOut
from app.domain.enums import TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks(container: ContainerDep, status: TaskStatus | None = None) -> list[TaskOut]:
    return [TaskOut.of(view) for view in container.queries.tasks(status)]


@router.post("/{task_id}/approve")
def approve(task_id: int, container: ContainerDep) -> TaskOut:
    task = container.approvals.approve(task_id, FARMER)
    return TaskOut.of(container.queries.task_view(task))


@router.post("/{task_id}/reject")
def reject(task_id: int, container: ContainerDep, body: RejectIn | None = None) -> TaskOut:
    task = container.approvals.reject(task_id, FARMER, body.reason if body else None)
    return TaskOut.of(container.queries.task_view(task))


@router.post("/{task_id}/revert")
def revert(task_id: int, container: ContainerDep) -> RevertOut:
    result = container.revert.revert(task_id, FARMER)
    return RevertOut(
        task=TaskOut.of(container.queries.task_view(result.task)),
        requested_mm=result.requested_mm,
        applied_mm=result.applied_mm,
        applied_liters=result.applied_liters,
    )
