"""The farmer chat: one orchestrator run per question, in its own session (D044, D053)."""

from collections.abc import Callable

from app.agent.loop import AgentRun
from app.persistence.ports import UnitOfWork
from app.services.agent_session import AgentDeps, AgentSession
from app.services.gate_context import local_day

UowFactory = Callable[[], UnitOfWork]


class ChatService:
    def __init__(self, uow: UowFactory, deps: AgentDeps) -> None:
        self._uow = uow
        self._deps = deps

    def ask(self, plot_id: int, question: str) -> AgentRun:
        """The answer is the output of answer_farmer: verified before it is returned."""
        with self._uow() as u:
            day = local_day(self._deps.clock.now(), u.plots.get(plot_id))
        return AgentSession(self._deps, plot_id, day).run("orchestrator", question)
