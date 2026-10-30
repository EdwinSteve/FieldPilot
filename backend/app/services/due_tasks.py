"""Run scheduled tasks whose time has come, re-evaluating each one first (D009, D033).

Called explicitly with the simulated time; there is no background thread
(D016). Nothing runs on a stale verdict.
"""

from collections.abc import Callable, Sequence
from datetime import datetime

from app.actuation.simulated import SUPPORTED_ACTIONS
from app.autonomy.gate import AutonomyGate, FarmerApproval, unapproved
from app.autonomy.messages import MessageCatalog
from app.domain.enums import EventKind, TaskStatus
from app.domain.models import Event, Notification, Task
from app.domain.verdicts import GateVerdict
from app.domain.violations import RuleCode, RuleViolation
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
                task
                for task in u.tasks.list(status=TaskStatus.SCHEDULED)
                if task.scheduled_for <= now and task.action_type in SUPPORTED_ACTIONS
            ]
        return [self.run_task(task, now) for task in due]

    def run_task(self, task: Task, now: datetime) -> Task:
        """Re-evaluate one due task and execute or fail it. An approved task carries its
        approval, which covers only the rules the farmer saw (D062)."""
        with self._uow() as u:
            action = action_for_task(u, task, proposed_by=ACTOR)
            approval = farmer_approval(u, task_id(task))
        context = self._context.context_for(action, exclude_task_id=task.id)
        if approval is None:
            authorization = self._gate.authorize(action, context)
            blocking = authorization.verdict.violations
        else:
            authorization = self._gate.authorize_approved(action, context, approval)
            blocking = unapproved(authorization.verdict, approval)
        if authorization.permit is not None:
            return self._executor.execute(task, authorization.permit, authorization.verdict)
        return self._fail(task, authorization.verdict, blocking, now)

    def _fail(
        self,
        task: Task,
        verdict: GateVerdict,
        blocking: Sequence[RuleViolation],
        now: datetime,
    ) -> Task:
        """The fresh verdict no longer allows it: fail it and name the rule (D033, D062)."""
        codes = ", ".join(v.code for v in blocking)
        rule = "; ".join(_lower_first(self._messages.render(v)) for v in blocking)
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


def farmer_approval(u: UnitOfWork, stored_id: int) -> FarmerApproval | None:
    """The approval recorded for a task, with the rule codes it covers (D062)."""
    events = u.events.list(task_id=stored_id, kind=EventKind.APPROVAL)
    if not events:
        return None
    codes = events[-1].inputs.get("approved_codes")
    if not isinstance(codes, list):
        raise ValueError(f"approval of task {stored_id} has no approved_codes")
    return FarmerApproval(events[-1].actor, frozenset(RuleCode(str(code)) for code in codes))


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]
