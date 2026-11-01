"""The two-day demo of D076, step by step, exactly as the dashboard does it.

Shared by `make record-demo` (against the real model) and the replay test
(against the recordings). Each step is the same call the dashboard makes,
with the same actor, so a recording replays only on the same clicks.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.agent.llm.ports import LLMClient
from app.api.deps import FARMER
from app.container import Container
from app.domain.enums import TaskStatus
from app.services.daily_cycle import DailyCycle, DailyCycleResult
from app.simulator.scenarios import DroughtScenario

REJECT_REASON = "Esperaré la lluvia"  # the farmer's answer to the rain hold on day 1
DROUGHT = timedelta(hours=48)  # the dashboard's "Inyectar sequía (48 h)"
ONE_DAY = timedelta(days=1)  # the dashboard's "+1 día"


@dataclass(frozen=True)
class DayResult:
    day: date
    cycle: DailyCycleResult


def run_day(container: Container, plot_id: int, llm: LLMClient) -> DayResult:
    """ "Ejecutar ciclo diario" on the plot's current local day."""
    day = container.queries.local_day(plot_id)
    cycle = DailyCycle(container.runtime.uow, container.agent_deps(llm), container.config.messages)
    return DayResult(day, cycle.run(plot_id))


def reject_held(container: Container) -> list[int]:
    """ "Rechazar" with the demo's reason on every task waiting for the farmer."""
    held = container.queries.tasks(TaskStatus.PENDING_APPROVAL)
    for view in held:
        if view.task.id is not None:
            container.approvals.reject(view.task.id, FARMER, REJECT_REASON)
    return [view.task.id for view in held if view.task.id is not None]


def between_days(container: Container) -> None:
    """ "Inyectar sequía (48 h)", then "+1 día", which advances and ticks."""
    now = container.runtime.clock.now()
    container.scenarios.inject(DroughtScenario(now, now + DROUGHT), FARMER)
    container.clock_service.advance(FARMER, ONE_DAY)
    container.ticker.tick()
