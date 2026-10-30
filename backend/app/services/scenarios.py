"""Simulator scenarios as the dashboard sees them, from the simulator only (D014, D067)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import EventKind
from app.domain.errors import ScenarioRejectedError
from app.domain.models import JsonObject
from app.persistence.ports import UnitOfWork
from app.services.simulation import inject_scenario
from app.simulator.clock import Clock
from app.simulator.field import FieldSimulator
from app.simulator.scenarios import Scenario

UowFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True)
class ScenarioStatus:
    active: tuple[JsonObject, ...]  # applied now
    upcoming: tuple[JsonObject, ...]  # held by the simulator, not started yet
    lost: tuple[JsonObject, ...]  # logged, not ended, but no longer held: a restart (D014)


class ScenarioService:
    def __init__(self, uow: UowFactory, clock: Clock, simulator: FieldSimulator) -> None:
        self._uow = uow
        self._clock = clock
        self._simulator = simulator

    def status(self) -> ScenarioStatus:
        """What the simulator applies; the log only tells which scenarios were lost."""
        now = self._clock.now()
        held = self._simulator.scenarios()
        with self._uow() as u:
            logged = [e.inputs for e in u.events.list(kind=EventKind.SCENARIO_INJECTED)]
        known = [s.describe() for s in held]
        return ScenarioStatus(
            active=tuple(s.describe() for s in self._simulator.active_scenarios(now)),
            upcoming=tuple(s.describe() for s in held if s.start > now),
            lost=tuple(e for e in logged if _not_ended(e, now) and e not in known),
        )

    def inject(self, scenario: Scenario, actor: str) -> JsonObject:
        if scenario.start < self._clock.now():
            raise ScenarioRejectedError(
                f"the {scenario.name} scenario cannot start before the simulated time"
            )
        inject_scenario(self._simulator, scenario, self._uow, self._clock, actor)
        return scenario.describe()


def _not_ended(inputs: JsonObject, now: datetime) -> bool:
    end = inputs.get("end")
    return isinstance(end, str) and datetime.fromisoformat(end) > now
