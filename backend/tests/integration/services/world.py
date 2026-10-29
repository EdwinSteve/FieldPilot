"""A stored field with real services on an in-memory database, for step 6 tests."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.actuation.emergency import StoredEmergencyStop
from app.actuation.simulated import SimulatedActuator
from app.autonomy.gate import AutonomyGate, ExecutionPermit
from app.autonomy.messages import load_message_catalog
from app.autonomy.policy import load_autonomy_policy
from app.domain.enums import ActionType, EventKind, SensorKind
from app.domain.models import CropCycle, Event, Plot, Reading, Sensor, Task, Zone
from app.domain.proposals import ParamValue, ProposedAction
from app.persistence.ports import UnitOfWork
from app.phenology.catalog import load_crop_catalog
from app.safety.limits import load_safety_limits
from app.services.due_tasks import DueTaskRunner
from app.services.execution import ExecutionService
from app.services.gate_context import StoredGateContextProvider
from app.services.proposals import ProposalService
from app.services.revert import RevertService
from app.simulator.clock import Clock
from app.simulator.field import FieldSimulator
from app.simulator.water_balance import SoilParams
from tests.conftest import CONFIG_DIR, CROPS_DIR
from tests.fakes import FakeClock

# 06:00 local in Neiva (UTC-5) on 2026-10-28.
DAY1 = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)
WINDOW = timedelta(seconds=21600)  # autonomy.yaml
RATE = 6.0  # actuation.yaml
ZONE_AREA_HA = 0.5  # 5000 m2: 1 mm is 5000 L
POLICY = load_autonomy_policy(CONFIG_DIR / "autonomy.yaml")
LIMITS = load_safety_limits(CONFIG_DIR / "safety.yaml")
MESSAGES = load_message_catalog(CONFIG_DIR / "messages" / "es.yaml")
CROPS = load_crop_catalog(CROPS_DIR, LIMITS.max_moisture_pct_fc)


class FakeForecast:
    def __init__(self, mm: float | None = 0.0) -> None:
        self.mm = mm

    def rain_mm_next_24h(self, plot_id: int, at: datetime) -> float | None:
        return self.mm


class World:
    """Plot, zone, soil sensor with a reading, and an active maize cycle at sowing."""

    def __init__(self, uow: Callable[[], UnitOfWork], clock: Clock | None = None) -> None:
        self.uow = uow
        self.clock: Any = clock or FakeClock(DAY1)
        self.forecast = FakeForecast()
        self.emergency = StoredEmergencyStop(uow)
        with uow() as u:
            plot = u.plots.add(Plot("Neiva", 2.93, -75.28, 2.0, DAY1, utc_offset_hours=-5.0))
            assert plot.id is not None
            zone = u.zones.add(Zone(plot.id, "Zona 2", ZONE_AREA_HA, 32.0, valve_id="v2"))
            assert zone.id is not None
            sensor = u.sensors.add(Sensor(zone.id, SensorKind.SOIL_MOISTURE, "%"))
            assert sensor.id is not None
            u.readings.add_many([Reading(sensor.id, 20.0, DAY1)])  # 62,5 % of FC
            u.cycles.add(CropCycle(plot.id, "maize", date(2026, 10, 1)))
            u.commit()
        self.plot_id, self.zone_id = plot.id, zone.id
        self.build_services()

    def build_services(self, actuator: Any = None) -> None:
        """(Re)build the services; a new simulator models a process restart (D014)."""
        if actuator is None:
            self.valves = FieldSimulator(start=self.clock.now())
            self.valves.add_zone(self.zone_id, SoilParams(), initial_vwc=20.0)
            actuator = SimulatedActuator(self.valves, self.emergency, self.clock, RATE)
        self.actuator = actuator
        self.gate = AutonomyGate(POLICY, LIMITS)
        self.context = StoredGateContextProvider(self.uow, self.forecast, CROPS)
        self.executor = ExecutionService(self.uow, self.clock, actuator, MESSAGES)
        self.proposals = ProposalService(
            self.uow, self.clock, self.gate, self.context, self.executor, MESSAGES, WINDOW
        )
        self.due = DueTaskRunner(self.uow, self.gate, self.context, self.executor, MESSAGES)
        self.revert = RevertService(self.uow, self.clock, actuator)

    def action(
        self,
        action_type: ActionType = ActionType.IRRIGATION,
        volume_mm: float = 15.0,
        at: datetime | None = None,
        params: dict[str, ParamValue] | None = None,
        rationale: str = "Humedad 62 % de CC, sin lluvia prevista.",
    ) -> ProposedAction:
        scheduled = at or self.clock.now()
        return ProposedAction.create(
            action_type=action_type,
            plot_id=self.plot_id,
            zone_id=self.zone_id,
            scheduled_for=scheduled,
            local_day=(scheduled - timedelta(hours=5)).date(),
            params={"volume_mm": volume_mm} if params is None else params,
            rationale=rationale,
            proposed_by="agent:irrigation",
        )

    def events(self, kind: EventKind | None = None, task_id: int | None = None) -> list[Event]:
        with self.uow() as u:
            return list(u.events.list(task_id=task_id, kind=kind))

    def task(self, task_id: int | None) -> Task:
        assert task_id is not None
        with self.uow() as u:
            return u.tasks.get(task_id)

    def valve_open(self) -> bool:
        return self.valves.status(self.zone_id, self.clock.now()).is_open

    def set_emergency_stop(self, active: bool) -> None:
        with self.uow() as u:
            u.control.set_emergency_stop(
                active,
                Event(EventKind.EMERGENCY_STOP, "farmer", "test", self.clock.now()),
            )
            u.commit()

    def permit(self, action: ProposedAction) -> ExecutionPermit:
        auth = self.gate.authorize(action, self.context.context_for(action))
        assert auth.permit is not None, auth.verdict
        return auth.permit
