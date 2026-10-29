"""ProposalService: the only entry point of the execution path (architecture §4.3)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from app.autonomy.gate import AutonomyGate
from app.autonomy.messages import MessageCatalog
from app.domain.enums import EventKind, GateOutcome, TaskStatus
from app.domain.errors import MissingDataError
from app.domain.models import Decision, Event, JsonValue, Notification, Task
from app.domain.proposals import ProposedAction
from app.domain.verdicts import GateVerdict
from app.persistence.ports import UnitOfWork
from app.services.execution import ExecutionService
from app.services.gate_context import GateContextProvider, active_cycle
from app.services.gate_decisions import (
    append_verdict,
    proposal_json,
    verdict_from_event,
    verdict_json,
    verdict_reason,
)
from app.simulator.clock import Clock

UowFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True)
class ProposalResult:
    task: Task
    verdict: GateVerdict
    already_decided_at: datetime | None  # set when the same proposal came before (D023)


class ProposalPort(Protocol):
    def propose(self, action: ProposedAction) -> ProposalResult: ...


class ProposalService:
    def __init__(
        self,
        uow: UowFactory,
        clock: Clock,
        gate: AutonomyGate,
        context: GateContextProvider,
        executor: ExecutionService,
        messages: MessageCatalog,
        revert_window: timedelta,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._gate = gate
        self._context = context
        self._executor = executor
        self._messages = messages
        self._revert_window = revert_window

    def propose(self, action: ProposedAction) -> ProposalResult:
        """Decide, commit the task, and run it now if allowed and due.

        A repeated proposal returns its earlier task and verdict and does
        nothing else (D023).
        """
        earlier = self._earlier(action)
        if earlier is not None:
            return earlier
        context = self._context.context_for(action)
        authorization = self._gate.authorize(action, context)
        verdict = authorization.verdict
        now = self._clock.now()
        with self._uow() as u:
            task = u.tasks.add(self._task(u, action, verdict, now), _proposal_event(action, now))
            stored_id = _stored_id(task)
            append_verdict(u, now, action, context, verdict, task_id=stored_id)
            u.decisions.add(_decision(stored_id, action, verdict, now))
            if verdict.outcome is GateOutcome.EXECUTE_AND_NOTIFY:
                self._notify(u, task, now)
            u.commit()
        if authorization.permit is not None and task.scheduled_for <= now:
            task = self._executor.execute(task, authorization.permit)
        return ProposalResult(task, verdict, already_decided_at=None)

    def _earlier(self, action: ProposedAction) -> ProposalResult | None:
        with self._uow() as u:
            proposal = u.events.find_by_key(EventKind.PROPOSAL, action.proposal_key)
            if proposal is None or proposal.task_id is None:
                return None
            verdict_event = u.events.find_by_key(EventKind.GATE_VERDICT, action.proposal_key)
            if verdict_event is None:
                raise MissingDataError(f"proposal {action.proposal_key} has no stored verdict")
            task = u.tasks.get(proposal.task_id)
        return ProposalResult(task, verdict_from_event(verdict_event), proposal.occurred_at)

    def _task(
        self, u: UnitOfWork, action: ProposedAction, verdict: GateVerdict, now: datetime
    ) -> Task:
        notify = verdict.outcome is GateOutcome.EXECUTE_AND_NOTIFY
        awaiting = verdict.outcome is GateOutcome.AWAIT_APPROVAL
        return Task(
            cycle_id=_stored_cycle_id(u, action.plot_id),
            zone_id=action.zone_id,
            action_type=action.action_type,
            params=dict(action.params),
            scheduled_for=action.scheduled_for,
            status=TaskStatus.PENDING_APPROVAL if awaiting else TaskStatus.SCHEDULED,
            effective_level=verdict.effective_level,
            rationale=action.rationale,
            estimated_cost=action.estimated_cost,
            # Simulated time, decided by the backend and stored (D011).
            revert_deadline=now + self._revert_window if notify else None,
            created_at=now,
            updated_at=now,
        )

    def _notify(self, u: UnitOfWork, task: Task, now: datetime) -> None:
        message = self._messages.label("notify_committed")
        u.notifications.add(
            Notification(message, now, task_id=task.id, revert_deadline=task.revert_deadline)
        )
        deadline = task.revert_deadline.isoformat() if task.revert_deadline else None
        u.events.append(
            Event(
                kind=EventKind.NOTIFICATION,
                actor="system:proposals",
                reason="Farmer notified of a NOTIFY action and its revert window.",
                occurred_at=now,
                task_id=task.id,
                autonomy_level=task.effective_level,
                inputs={"revert_deadline": deadline},
            )
        )


def _proposal_event(action: ProposedAction, now: datetime) -> Event:
    return Event(
        kind=EventKind.PROPOSAL,
        actor=action.proposed_by,
        reason=f"{action.action_type} proposed: {action.rationale}",
        occurred_at=now,
        idempotency_key=action.proposal_key,  # one task per proposal (D023)
        inputs={"proposal": proposal_json(action)},
    )


def _decision(
    task_id: int, action: ProposedAction, verdict: GateVerdict, now: datetime
) -> Decision:
    violations: tuple[dict[str, JsonValue], ...] = tuple(
        {"code": v.code, "params": dict(v.params)} for v in verdict.violations
    )
    return Decision(
        task_id=task_id,
        requested_level=verdict.requested_level,
        effective_level=verdict.effective_level,
        outcome=verdict.outcome,
        reason=verdict_reason(action, verdict),
        created_at=now,
        violations=violations,
        inputs={"verdict": verdict_json(verdict)},
    )


def _stored_cycle_id(u: UnitOfWork, plot_id: int) -> int:
    cycle = active_cycle(u, plot_id)
    if cycle.id is None:
        raise MissingDataError(f"plot {plot_id} has an unsaved cycle")
    return cycle.id


def _stored_id(task: Task) -> int:
    if task.id is None:
        raise RuntimeError("database did not assign a task id")
    return task.id
