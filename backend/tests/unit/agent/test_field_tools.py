import json

import pytest

from app.agent.brief import ObservationKind, ObservationLedger
from app.agent.tools.field_tools import ReadContext, read_tools
from app.agent.tools.registry import ToolRegistry
from app.domain.models import JsonObject
from tests.unit.agent.field_fakes import NOW, FakeReader


@pytest.fixture
def ledger() -> ObservationLedger:
    return ObservationLedger()


def _tools(ledger: ObservationLedger, rain: float | None = 0.0) -> ToolRegistry:
    return ToolRegistry(read_tools(ReadContext(1, FakeReader(rain), ledger, lambda: NOW)))


def _call(registry: ToolRegistry, name: str, **args: object) -> JsonObject:
    outcome = registry.call(name, json.dumps(args))
    assert outcome.error is None and outcome.result is not None
    return outcome.result


def test_no_read_tool_writes_or_closes(ledger: ObservationLedger) -> None:
    for name in ("list_zones", "read_zone", "read_forecast", "read_crop_stage"):
        tool = _tools(ledger).get(name)
        assert tool is not None and not tool.writes and not tool.closes_run


def test_list_zones(ledger: ObservationLedger) -> None:
    result = _call(_tools(ledger), "list_zones")

    assert result == {"zones": [{"zone_id": 2, "name": "Zone 2"}, {"zone_id": 3, "name": "Zone 3"}]}
    assert len(ledger) == 0


def test_read_zone_records_every_value_it_returns(ledger: ObservationLedger) -> None:
    result = _call(_tools(ledger), "read_zone", zone_id=2)

    assert result["soil_moisture"] == {
        "observation_id": "reading-412",
        "value": 21.0,
        "unit": "%",
        "at": "2026-10-28T10:50:00+00:00",
    }
    assert result["field_capacity"] == {
        "observation_id": "zone-2-field-capacity",
        "value": 32.0,
        "unit": "%",
        "at": None,
    }
    last = result["last_irrigation"]
    assert isinstance(last, dict) and last["observation_id"] == "task-7"
    assert last["value"] == 15.0 and last["status"] == "executed"
    upcoming = result["upcoming"]
    assert isinstance(upcoming, list) and upcoming[0] == {
        "observation_id": "task-9",
        "value": 10.0,
        "unit": "mm",
        "at": "2026-10-29T11:00:00+00:00",
        "task_id": 9,
        "action_type": "extra_irrigation",
        "status": "scheduled",
    }
    moisture = ledger.get("reading-412")
    assert moisture is not None and moisture.kind is ObservationKind.SOIL_MOISTURE
    assert all(ledger.get(oid) for oid in ("zone-2-field-capacity", "task-7", "task-9"))
    assert len(ledger) == 4


def test_a_zone_without_readings_has_null_moisture(ledger: ObservationLedger) -> None:
    result = _call(_tools(ledger), "read_zone", zone_id=3)

    assert result["soil_moisture"] is None
    assert result["last_irrigation"] is None
    assert len(ledger) == 1  # only the field capacity


def test_a_zone_of_another_plot_is_refused(ledger: ObservationLedger) -> None:
    outcome = _tools(ledger).call("read_zone", '{"zone_id": 99}')

    assert outcome.error == "Zone 99 is not in this plot. Call list_zones for the valid ids."
    assert len(ledger) == 0


def test_read_forecast_records_the_value_with_the_time(ledger: ObservationLedger) -> None:
    result = _call(_tools(ledger, rain=3.5), "read_forecast")

    assert result == {
        "rain_next_24h": {
            "observation_id": "forecast-plot-1-2026-10-28T11:00Z",
            "value": 3.5,
            "unit": "mm",
            "at": "2026-10-28T11:00:00+00:00",
        },
        "note": None,
    }
    assert ledger.get("forecast-plot-1-2026-10-28T11:00Z") is not None


def test_an_unknown_forecast_says_the_gate_will_hold(ledger: ObservationLedger) -> None:
    result = _call(_tools(ledger, rain=None), "read_forecast")

    rain = result["rain_next_24h"]
    assert isinstance(rain, dict) and rain["value"] is None
    assert result["note"] == "Unknown forecast: the gate holds any irrigation for approval."


def test_read_crop_stage_records_stage_gdd_and_kc(ledger: ObservationLedger) -> None:
    result = _call(_tools(ledger), "read_crop_stage")

    assert result["stage"] == {
        "observation_id": "stage-cycle-4",
        "value": "v6",
        "unit": "",
        "at": None,
        "display_es": "V6 (seis hojas)",
    }
    gdd = result["accumulated_gdd"]
    assert isinstance(gdd, dict) and (gdd["value"], gdd["unit"]) == (412.5, "GDD")
    assert ledger.get("kc-cycle-4") is not None


def test_extra_arguments_are_refused(ledger: ObservationLedger) -> None:
    outcome = _tools(ledger).call("read_forecast", '{"days": 3}')

    assert outcome.error is not None and outcome.error.startswith("Invalid arguments: days")
