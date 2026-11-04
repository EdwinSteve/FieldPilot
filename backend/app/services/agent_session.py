"""One agent session: a ledger, a brief and a loop for one daily cycle or chat turn.

Tools are bound to their session, so nothing an agent reads in one session
can be cited in another.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from app.agent.brief import BriefDraft, ObservationLedger
from app.agent.field import ActionProposer, Agronomy, FarmerOutbox, FieldReader, ImageryReader
from app.agent.llm.ports import LLMClient
from app.agent.loop import AgentLoop, AgentRun, RunStatus, Subagent
from app.agent.toolbox import cycle_registry
from app.agent.tools.field_tools import ReadContext
from app.agent.trace import TraceSink
from app.simulator.clock import Clock

CONSULT_RESUMES = 2


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
    agronomy: Agronomy | None = None  # D093; None: the agronomy tools refuse


class AgentSession:
    def __init__(self, deps: AgentDeps, plot_id: int, day: date) -> None:
        self.session_id = deps.new_id()
        self.ledger = ObservationLedger()
        self.draft = BriefDraft(plot_id, day)
        read = ReadContext(plot_id, deps.reader, self.ledger, deps.clock.now)
        registry = cycle_registry(
            read, self.draft, deps.proposer, deps.outbox, self, deps.imagery, deps.agronomy
        )
        self.runs: list[AgentRun] = []  # every run of the session, nested ones first (D093)
        self.loop = AgentLoop(deps.llm, registry, deps.trace, deps.subagents, deps.max_turns)

    def consult(self, subagent: str, task: str) -> AgentRun:
        """Run a subagent in this session (the consult tools), resuming a pause (D046, D093).

        A consult is one step of the agronomist's run: a dropped model call is
        retried from the specialist's transcript, at most CONSULT_RESUMES times,
        instead of leaving the agronomist without that specialist.
        """
        run = self.run(subagent, task)
        for _ in range(CONSULT_RESUMES):
            if run.status is not RunStatus.PAUSED:
                break
            run = self.loop.resume(run)
            self.runs[-1] = run
        return run

    def run(self, subagent: str, task: str) -> AgentRun:
        count = sum(1 for r in self.runs if r.subagent == subagent)
        suffix = "" if count == 0 else f"-{count + 1}"  # a specialist consulted twice
        run = self.loop.run(subagent, task, f"{self.session_id}-{subagent}{suffix}")
        self.runs.append(run)
        return run
