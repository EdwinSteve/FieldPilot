import json

import pytest

from app.agent.tools.registry import Tool, ToolRegistry
from app.domain.errors import ConfigError
from app.domain.models import JsonObject
from tests.unit.agent.agents import Calls, ZoneArgs, make_registry


@pytest.fixture
def calls() -> Calls:
    return Calls()


@pytest.fixture
def registry(calls: Calls) -> ToolRegistry:
    return make_registry(calls)


def test_valid_call_returns_the_handler_result(registry: ToolRegistry, calls: Calls) -> None:
    outcome = registry.call("read_moisture", '{"zone_id": 2}')

    assert outcome.error is None
    assert outcome.result == {"zone_id": 2, "moisture_pct": 21.0, "observation_id": "reading-7"}
    assert outcome.arguments == {"zone_id": 2}
    assert outcome.closes_run is False
    assert calls.read_moisture == 1


def test_unknown_tool_lists_the_available_ones(registry: ToolRegistry) -> None:
    outcome = registry.call("open_valve", "{}")

    assert outcome.error == (
        "Unknown tool 'open_valve'. Available: read_moisture, submit_assessment."
    )
    assert json.loads(outcome.output_json()) == {"error": outcome.error}


def test_invalid_json_is_an_error_with_the_raw_text(registry: ToolRegistry) -> None:
    outcome = registry.call("read_moisture", '{"zone_id": ')

    assert outcome.error is not None and outcome.error.startswith("Arguments are not valid JSON")
    assert outcome.arguments == '{"zone_id": '


def test_arguments_must_be_an_object(registry: ToolRegistry) -> None:
    outcome = registry.call("read_moisture", "[2]")

    assert outcome.error == "Arguments must be a JSON object."


def test_validation_error_names_the_field(registry: ToolRegistry, calls: Calls) -> None:
    outcome = registry.call("read_moisture", '{"zone_id": 0}')

    assert outcome.error is not None
    assert outcome.error.startswith("Invalid arguments: zone_id:")
    assert calls.read_moisture == 0


def test_missing_field_is_a_validation_error(registry: ToolRegistry) -> None:
    outcome = registry.call("read_moisture", "{}")

    assert outcome.error == "Invalid arguments: zone_id: Field required."


def test_a_refusal_from_the_check_goes_back_to_the_model(registry: ToolRegistry) -> None:
    outcome = registry.call("submit_assessment", '{"summary": "dry", "moisture_pct": 30}')

    assert outcome.error == "moisture_pct 30.0 matches no stored reading."
    assert outcome.closes_run is False


def test_only_a_successful_closing_call_closes_the_run(registry: ToolRegistry) -> None:
    outcome = registry.call("submit_assessment", '{"summary": "dry", "moisture_pct": 21}')

    assert outcome.closes_run is True
    assert outcome.result == {"accepted": True, "summary": "dry"}


def test_a_handler_bug_propagates() -> None:
    def broken(args: ZoneArgs) -> JsonObject:
        raise RuntimeError("bug")

    registry = ToolRegistry([Tool("broken", "Fails.", ZoneArgs, broken)])

    with pytest.raises(RuntimeError, match="bug"):
        registry.call("broken", '{"zone_id": 1}')


def test_duplicate_tool_names_are_refused(registry: ToolRegistry) -> None:
    with pytest.raises(ConfigError, match="registered twice"):
        registry.register(Tool("read_moisture", "Again.", ZoneArgs, Calls().read))


def test_subset_keeps_only_the_named_tools(registry: ToolRegistry) -> None:
    subset = registry.subset(["read_moisture"])

    assert subset.names() == frozenset({"read_moisture"})
    assert subset.call("submit_assessment", "{}").error is not None


def test_subset_with_an_unknown_name_is_refused(registry: ToolRegistry) -> None:
    with pytest.raises(ConfigError, match="unknown tools: open_valve"):
        registry.subset(["read_moisture", "open_valve"])


def test_specs_carry_the_json_schema(registry: ToolRegistry) -> None:
    specs = {spec.name: spec for spec in registry.specs()}

    schema = specs["read_moisture"].parameters
    assert schema["required"] == ["zone_id"]
    assert specs["submit_assessment"].description.endswith("Closes the run.")
