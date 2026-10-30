"""A fake field for the agent tool tests: plot 1 with zones 2 and 3."""

from collections.abc import Sequence
from datetime import UTC, datetime

from app.agent.field import (
    ActionRequest,
    IrrigationRecord,
    MoistureReading,
    ProposalView,
    StageView,
    ZoneView,
)

NOW = datetime(2026, 10, 28, 11, 0, tzinfo=UTC)
ZONE_2 = ZoneView(
    zone_id=2,
    name="Zone 2",
    field_capacity_pct=32.0,
    moisture=MoistureReading(412, 21.0, datetime(2026, 10, 28, 10, 50, tzinfo=UTC)),
    last_irrigation=IrrigationRecord(
        7, "irrigation", 15.0, datetime(2026, 10, 27, 11, 0, tzinfo=UTC), "executed"
    ),
    upcoming=(
        IrrigationRecord(
            9, "extra_irrigation", 10.0, datetime(2026, 10, 29, 11, 0, tzinfo=UTC), "scheduled"
        ),
    ),
)
ZONE_3 = ZoneView(3, "Zone 3", 30.0, None, None, ())


class FakeReader:
    def __init__(self, rain: float | None = 0.0) -> None:
        self.rain = rain

    def zones(self, plot_id: int) -> Sequence[ZoneView]:
        return [ZONE_2, ZONE_3]

    def zone(self, plot_id: int, zone_id: int) -> ZoneView | None:
        return {2: ZONE_2, 3: ZONE_3}.get(zone_id)

    def rain_mm_next_24h(self, plot_id: int, at: datetime) -> float | None:
        return self.rain

    def crop_stage(self, plot_id: int) -> StageView:
        return StageView(4, "v6", "V6 (seis hojas)", 412.5, 0.71)


class FakeProposer:
    """Answers like the gate allowing the action; keeps every request."""

    def __init__(self, view: ProposalView | None = None) -> None:
        self.view = view or ProposalView(21, "executed", "execute", "autonomous", None, False)
        self.requests: list[ActionRequest] = []

    def propose(self, request: ActionRequest) -> ProposalView:
        self.requests.append(request)
        return self.view
