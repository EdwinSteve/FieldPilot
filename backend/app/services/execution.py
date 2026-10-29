"""Write-ahead execution (D013): request, act outside any transaction, then close.

1. Transaction A writes `execution_requested` with `task-{id}:attempt-{n}`.
2. The actuator runs, outside any transaction.
3. Transaction B writes `execution` (task EXECUTED) or `execution_failed`
   (task FAILED) with the same key.

A crash between 1 and 3 leaves an open request that startup reconciliation
resolves by key, so nothing ever runs twice.
"""

from collections.abc import Callable
from datetime import datetime

from app.actuation.ports import Actuator, ExecutionResult
from app.autonomy.gate import ExecutionPermit
from app.autonomy.messages import MessageCatalog
from app.domain.enums import EventKind, TaskStatus
from app.domain.errors import DomainError
from app.domain.models import Event, JsonValue, Notification, Task
from app.domain.verdicts import GateVerdict
from app.persistence.ports import UnitOfWork
from app.services.gate_decisions import verdict_json
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]
ACTOR = "system:executor"


class ExecutionService:
    def __init__(
        self, uow: UowFactory, clock: Clock, actuator: Actuator, messages: MessageCatalog
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._actuator = actuator
        self._messages = messages

    def execute(
        self, task: Task, permit: ExecutionPermit, recheck: GateVerdict | None = None
    ) -> Task:
        """Run `task` under `permit`. `recheck` is the fresh verdict of a due task (D033)."""
        key = self._request(task, permit, recheck)
        try:
            result = self._actuator.execute(permit, task, key)
        except DomainError as error:
            return self._close_failed(task_id(task), key, str(error))
        return self._close_executed(task_id(task), key, result)

    def _request(self, task: Task, permit: ExecutionPermit, recheck: GateVerdict | None) -> str:
        """Transaction A: the request is durable before anything physical happens."""
        with self._uow() as u:
            attempt = len(u.events.list(task_id=task_id(task), kind=EventKind.EXECUTION_REQUESTED))
            key = f"task-{task_id(task)}:attempt-{attempt + 1}"
            inputs: dict[str, JsonValue] = {"proposal_key": permit.proposal_key}
            if recheck is not None:
                inputs["recheck_verdict"] = verdict_json(recheck)
            u.events.append(
                Event(
                    kind=EventKind.EXECUTION_REQUESTED,
                    actor=ACTOR,
                    reason=f"Execution of {task.action_type} requested.",
                    occurred_at=self._clock.now(),
                    task_id=task.id,
                    autonomy_level=permit.level,
                    idempotency_key=key,
                    inputs=inputs,
                )
            )
            u.commit()
        return key

    def _close_executed(self, stored_id: int, key: str, result: ExecutionResult) -> Task:
        """Transaction B: the real result, with the same key."""
        with self._uow() as u:
            task = u.tasks.transition(
                stored_id, TaskStatus.EXECUTED, execution_event(result, self._clock.now())
            )
            u.commit()
        return task

    def _close_failed(self, stored_id: int, key: str, error: str) -> Task:
        now = self._clock.now()
        with self._uow() as u:
            task = u.tasks.transition(
                stored_id,
                TaskStatus.FAILED,
                Event(
                    kind=EventKind.EXECUTION_FAILED,
                    actor=ACTOR,
                    reason=f"Actuator refused the command: {error}",
                    occurred_at=now,
                    idempotency_key=key,
                    inputs={"error": error},
                ),
            )
            message = self._messages.label("execution_failed", task_id=str(stored_id))
            u.notifications.add(Notification(message, now, task_id=stored_id))
            u.commit()
        return task


def execution_event(result: ExecutionResult, at: datetime, reconciled: bool = False) -> Event:
    reason = "Command applied by the actuator."
    if reconciled:
        reason = "Command found in the actuator's records at startup; closed without retry."
    return Event(
        kind=EventKind.EXECUTION,
        actor=ACTOR,
        reason=reason,
        occurred_at=at,
        idempotency_key=result.idempotency_key,
        inputs={**result_json(result), "reconciled": reconciled},
    )


def result_json(result: ExecutionResult) -> dict[str, JsonValue]:
    return {
        "action_type": result.action_type,
        "zone_id": result.zone_id,
        "started_at": result.started_at.isoformat(),
        "target_mm": result.target_mm,
        "rate_mm_per_h": result.rate_mm_per_h,
        "applied_mm": result.applied_mm,
    }


def task_id(task: Task) -> int:
    if task.id is None:
        raise ValueError("task must be stored before it is executed")
    return task.id
