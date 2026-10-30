"""Implements the agent's `ActionProposer` port with ProposalService (principle 2)."""

from collections.abc import Callable

from app.agent.field import ActionRequest, ProposalView
from app.autonomy.messages import MessageCatalog
from app.domain.enums import ActionType
from app.domain.proposals import ProposedAction
from app.persistence.ports import UnitOfWork
from app.services.gate_context import local_day
from app.services.proposals import ProposalPort

UowFactory = Callable[[], UnitOfWork]


class GateProposer:
    """Turns an agent request into a `ProposedAction`; the gate decides as for anyone else."""

    def __init__(self, uow: UowFactory, proposals: ProposalPort, messages: MessageCatalog) -> None:
        self._uow = uow
        self._proposals = proposals
        self._messages = messages

    def propose(self, request: ActionRequest) -> ProposalView:
        with self._uow() as u:
            plot = u.plots.get(request.plot_id)
        action = ProposedAction.create(
            action_type=ActionType(request.action_type),
            plot_id=request.plot_id,
            zone_id=request.zone_id,
            scheduled_for=request.scheduled_for,
            local_day=local_day(request.scheduled_for, plot),
            params=request.params,
            rationale=request.rationale,
            proposed_by=request.proposed_by,
        )
        result = self._proposals.propose(action)
        verdict = result.verdict
        if result.task.id is None:
            raise RuntimeError("ProposalService returned an unsaved task")
        return ProposalView(
            task_id=result.task.id,
            status=str(result.task.status),
            outcome=str(verdict.outcome),
            effective_level=str(verdict.effective_level),
            reason_es=self._messages.render(verdict.violations[0]) if verdict.violations else None,
            already_decided=result.already_decided_at is not None,
        )
