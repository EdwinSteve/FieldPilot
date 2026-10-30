"""A fake field for the agent tool tests: plot 1 with zones 2 and 3."""

from collections.abc import Sequence
from datetime import UTC, date, datetime

from app.agent.field import (
    ActionRequest,
    ImageryView,
    IrrigationRecord,
    MoistureReading,
    ProposalView,
    StageView,
    ZoneImagery,
    ZoneView,
)
from app.agent.loop import AgentRun

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

    def task_status(self, plot_id: int, task_id: int) -> str | None:
        return {7: "executed", 9: "scheduled", 21: "executed"}.get(task_id)


class FakeProposer:
    """Answers like the gate allowing the action; keeps every request."""

    def __init__(self, view: ProposalView | None = None) -> None:
        self.view = view or ProposalView(21, "executed", "execute", "autonomous", None, False)
        self.requests: list[ActionRequest] = []

    def propose(self, request: ActionRequest) -> ProposalView:
        self.requests.append(request)
        return self.view


class FakeOutbox:
    """Keeps saved reports and notifications in memory."""

    def __init__(self) -> None:
        self.reports: list[str] = []
        self.notifications: list[str] = []

    def save_report(self, plot_id: int, text_es: str) -> int:
        self.reports.append(text_es)
        return len(self.reports)

    def notify(self, plot_id: int, text_key: str) -> None:
        self.notifications.append(text_key)


class NoConsultant:
    """For tests that never consult: any call is a test bug."""

    def consult(self, subagent: str, task: str) -> AgentRun:
        raise AssertionError(f"unexpected consult of {subagent}")


SCENE = ImageryView(
    "scene-1",
    date(2026, 10, 27),
    True,
    0.4,
    (ZoneImagery(2, 0.378, 21.2, 25.3), ZoneImagery(3, 0.802, 0.0, 0.0)),
    None,
)


class FakeImagery:
    """Returns a fixed view (or None for "no scene")."""

    def __init__(self, view: ImageryView | None = SCENE) -> None:
        self.view = view

    def imagery(self, plot_id: int, day: date) -> ImageryView | None:
        return self.view
