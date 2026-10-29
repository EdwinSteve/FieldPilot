"""Run scheduled tasks whose time has come, re-evaluating each one first (D009, D033).

Called explicitly with the simulated time; there is no background thread
(D016). Nothing runs on a stale verdict.
"""

from collections.abc import Callable, Sequence
from datetime import datetime

from app.actuation.simulated import SUPPORTED_ACTIONS
from app.autonomy.gate import AutonomyGate
from app.autonomy.messages import MessageCatalog
from app.domain.enums import EventKind, TaskStatus
from app.domain.models import Event, Notification, Task
from app.domain.verdicts import GateVerdict
from app.persistence.ports import UnitOfWork
from app.services.execution import ExecutionService, task_id
from app.services.gate_context import GateContextProvider, action_for_task
from app.services.gate_decisions import verdict_json

UowFactory = Callable[[], UnitOfWork]
ACTOR = "system:due_tasks"


class DueTaskRunner:
    def __init__(
        self,
        uow: UowFactory,
        gate: AutonomyGate,
        context: GateContextProvider,
        executor: ExecutionService,
        messages: MessageCatalog,
    ) -> None:
        self._uow = uow
        self._gate = gate
        self._context = context
        self._executor = executor
        self._messages = messages

    def run_due(self, now: datetime) -> Sequence[Task]:
        """Execute or fail every due task the actuator supports; return them updated."""
        with self._uow() as u:
            due = [
                (task, action_for_task(u, task, proposed_by=ACTOR))
                for task in u.tasks.list(status=TaskStatus.SCHEDULED)
                if task.scheduled_for <= now and task.action_type in SUPPORTED_ACTIONS
            ]
        results: list[Task] = []
        for task, action in due:
            context = self._context.context_for(action, exclude_task_id=task.id)
            authorization = self._gate.authorize(action, context)
            if authorization.permit is not None:
                results.append(
                    self._executor.execute(task, authorization.permit, authorization.verdict)
                )
            else:
                results.append(self._fail(task, authorization.verdict, now))
        return results

    def _fail(self, task: Task, verdict: GateVerdict, now: datetime) -> Task:
        """The fresh verdict no longer allows it: fail it and name the rule (D033)."""
        codes = ", ".join(v.code for v in verdict.violations)
        rule = "; ".join(_lower_first(self._messages.render(v)) for v in verdict.violations)
        with self._uow() as u:
            failed = u.tasks.transition(
                task_id(task),
                TaskStatus.FAILED,
                Event(
                    kind=EventKind.EXECUTION_FAILED,
                    actor=ACTOR,
                    reason=f"Not executed: re-evaluated at its time and set to "
                    f"{verdict.effective_level} because of: {codes}.",
                    occurred_at=now,
                    autonomy_level=verdict.effective_level,
                    rule=verdict.reason_code,
                    inputs={"recheck_verdict": verdict_json(verdict)},
                ),
            )
            message = self._messages.label("scheduled_not_executed", rule=rule)
            u.notifications.add(Notification(message, now, task_id=task.id))
            u.commit()
        return failed


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]
