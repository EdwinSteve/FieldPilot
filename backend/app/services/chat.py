"""The farmer chat: one orchestrator run per question, in its own session (D044, D053)."""

from collections.abc import Callable
from dataclasses import replace

from app.agent.loop import AgentRun
from app.agent.scope import is_out_of_scope
from app.persistence.ports import UnitOfWork
from app.services.agent_session import AgentDeps, AgentSession
from app.services.gate_context import local_day

UowFactory = Callable[[], UnitOfWork]


class ChatService:
    def __init__(self, uow: UowFactory, deps: AgentDeps, out_of_scope: str) -> None:
        self._uow = uow
        self._deps = deps
        self._out_of_scope = out_of_scope  # the fixed answer to an off-topic question (D088)

    def ask(self, plot_id: int, question: str) -> AgentRun:
        """The answer is the output of answer_farmer: verified before it is returned, or the
        fixed text when the question is not about the crop (D088)."""
        with self._uow() as u:
            day = local_day(self._deps.clock.now(), u.plots.get(plot_id))
        run = AgentSession(self._deps, plot_id, day).run("orchestrator", question)
        if is_out_of_scope(run.output) and isinstance(run.output, dict):
            return replace(run, output={**run.output, "answer": self._out_of_scope})
        return run
