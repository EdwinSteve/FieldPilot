"""The daily cycle: Monitoring -> Irrigation -> Reporting, in a fixed order (D044, D051).

It stops at the first subagent that does not complete. A turn limit is a
failure and the farmer is told; a pause is not, so it is only written to the
event log and the next run retries the cycle under new run ids (D048).
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.agent.brief import FieldBrief
from app.agent.loop import AgentRun, RunStatus
from app.autonomy.messages import MessageCatalog
from app.domain.enums import EventKind
from app.domain.models import Event
from app.persistence.ports import UnitOfWork
from app.services.agent_session import AgentDeps, AgentSession
from app.services.gate_context import local_day

UowFactory = Callable[[], UnitOfWork]
ACTOR = "system:daily_cycle"
ORDER = ("monitoring", "irrigation", "reporting")  # imaging joins in step 8
FAILED_TEXT = "cycle.failed_turn_limit"
PAUSED_TEXT = "cycle.paused_retry_next_run"


@dataclass(frozen=True)
class DailyCycleResult:
    session_id: str
    status: RunStatus  # COMPLETED only when every subagent completed
    runs: tuple[AgentRun, ...]
    stopped_at: str | None  # the subagent that did not complete
    brief: FieldBrief


class DailyCycle:
    def __init__(self, uow: UowFactory, deps: AgentDeps, messages: MessageCatalog) -> None:
        self._uow = uow
        self._deps = deps
        self._messages = messages

    def run(self, plot_id: int) -> DailyCycleResult:
        now = self._deps.clock.now()
        with self._uow() as u:
            day = local_day(now, u.plots.get(plot_id))
        session = AgentSession(self._deps, plot_id, day)
        runs: list[AgentRun] = []
        for subagent in ORDER:
            run = session.run(subagent, _task(subagent, plot_id, session))
            runs.append(run)
            if run.status is not RunStatus.COMPLETED:
                self._stopped(plot_id, session.session_id, run)
                return DailyCycleResult(
                    session.session_id, run.status, tuple(runs), subagent, session.draft.freeze()
                )
        return DailyCycleResult(
            session.session_id, RunStatus.COMPLETED, tuple(runs), None, session.draft.freeze()
        )

    def _stopped(self, plot_id: int, session_id: str, run: AgentRun) -> None:
        if run.status is RunStatus.TURN_LIMIT:
            self._deps.outbox.notify(plot_id, FAILED_TEXT)
            return
        # D051: a pause is not a failure. Logged, never shown as an alert.
        now = self._deps.clock.now()
        with self._uow() as u:
            u.events.append(
                Event(
                    kind=EventKind.AGENT_TOOL_CALL,
                    actor=ACTOR,
                    reason=self._messages.agent_text(PAUSED_TEXT),
                    occurred_at=now,
                    inputs={
                        "session_id": session_id,
                        "run_id": run.run_id,
                        "subagent": run.subagent,
                        "tool": None,
                        "text_key": PAUSED_TEXT,
                    },
                    idempotency_key=f"daily-cycle-{session_id}:paused",
                )
            )
            u.commit()


def _task(subagent: str, plot_id: int, session: AgentSession) -> str:
    day = session.draft.day.isoformat()
    if subagent == "monitoring":
        return f"Assess every zone of plot {plot_id} for {day}."
    brief = session.draft.freeze().to_json()
    if subagent == "irrigation":
        return f"Decide the irrigation of plot {plot_id} for {day}. Brief: {brief}"
    return f"Write the report of plot {plot_id} for {day}. Brief: {brief}"
