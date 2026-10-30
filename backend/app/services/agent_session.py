"""One agent session: a ledger, a brief and a loop for one daily cycle or chat turn.

Tools are bound to their session, so nothing an agent reads in one session
can be cited in another.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from app.agent.brief import BriefDraft, ObservationLedger
from app.agent.field import ActionProposer, FarmerOutbox, FieldReader, ImageryReader
from app.agent.llm.ports import LLMClient
from app.agent.loop import AgentLoop, AgentRun, Subagent
from app.agent.toolbox import cycle_registry
from app.agent.tools.field_tools import ReadContext
from app.agent.trace import TraceSink
from app.simulator.clock import Clock


@dataclass(frozen=True)
class AgentDeps:
    """Everything a session needs, wired once at startup."""

    llm: LLMClient
    reader: FieldReader
    proposer: ActionProposer
    outbox: FarmerOutbox
    trace: TraceSink
    imagery: ImageryReader
    clock: Clock
    subagents: Sequence[Subagent]
    max_turns: int
    new_id: Callable[[], str]  # uuid4 hex in production; a counter in tests


class AgentSession:
    def __init__(self, deps: AgentDeps, plot_id: int, day: date) -> None:
        self.session_id = deps.new_id()
        self.ledger = ObservationLedger()
        self.draft = BriefDraft(plot_id, day)
        read = ReadContext(plot_id, deps.reader, self.ledger, deps.clock.now)
        registry = cycle_registry(read, self.draft, deps.proposer, deps.outbox, self, deps.imagery)
        self.loop = AgentLoop(deps.llm, registry, deps.trace, deps.subagents, deps.max_turns)

    def consult(self, subagent: str, task: str) -> AgentRun:
        """Run a subagent in this session (the orchestrator's consult tools)."""
        return self.run(subagent, task)

    def run(self, subagent: str, task: str) -> AgentRun:
        return self.loop.run(subagent, task, f"{self.session_id}-{subagent}")
