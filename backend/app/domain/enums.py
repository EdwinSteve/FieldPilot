"""Domain enumerations shared by every module."""

from enum import StrEnum


class AutonomyLevel(StrEnum):
    """How much the agent may do on its own. Ordered by strictness."""

    AUTONOMOUS = "autonomous"
    NOTIFY = "notify"
    APPROVAL = "approval"


_STRICTNESS: dict[AutonomyLevel, int] = {
    AutonomyLevel.AUTONOMOUS: 0,
    AutonomyLevel.NOTIFY: 1,
    AutonomyLevel.APPROVAL: 2,
}


def strictest(first: AutonomyLevel, *others: AutonomyLevel) -> AutonomyLevel:
    """Return the strictest of the given levels (APPROVAL > NOTIFY > AUTONOMOUS)."""
    return max((first, *others), key=_STRICTNESS.__getitem__)


class ActionType(StrEnum):
    """Every kind of action the agent can propose."""

    IRRIGATION = "irrigation"
    EXTRA_IRRIGATION = "extra_irrigation"
    STOP_IRRIGATION = "stop_irrigation"
    STRESS_ALERT = "stress_alert"
    STAGE_REPORT = "stage_report"
    CALENDAR_SHIFT = "calendar_shift"
    SCOUTING_VISIT = "scouting_visit"
    FERTILIZER = "fertilizer"
    AGROCHEMICAL = "agrochemical"
    PLANTING_DATE_CHANGE = "planting_date_change"
    HARVEST_TIMING = "harvest_timing"
    PRODUCT_LISTING = "product_listing"
    PRICE_CHANGE = "price_change"
    CHEMICAL_INJECTION = "chemical_injection"  # never executable (D005)


class TaskStatus(StrEnum):
    """Lifecycle of a task. Transitions are defined in `task_transitions`."""

    PENDING_APPROVAL = "pending_approval"
    SCHEDULED = "scheduled"
    EXECUTED = "executed"
    REVERTED = "reverted"
    REJECTED = "rejected"
    FAILED = "failed"


class GateOutcome(StrEnum):
    """Result of `AutonomyGate.evaluate()`; one per autonomy level (D004)."""

    EXECUTE = "execute"
    EXECUTE_AND_NOTIFY = "execute_notify"
    AWAIT_APPROVAL = "await_approval"


class EventKind(StrEnum):
    """Kinds of entries in the append-only event log."""

    PROPOSAL = "proposal"
    GATE_VERDICT = "gate_verdict"
    EXECUTION_REQUESTED = "execution_requested"
    EXECUTION = "execution"
    EXECUTION_FAILED = "execution_failed"
    REVERT = "revert"
    REVERT_REFUSED = "revert_refused"
    APPROVAL = "approval"
    REJECTION = "rejection"
    NOTIFICATION = "notification"
    EMERGENCY_STOP = "emergency_stop"
    STAGE_TRANSITION = "stage_transition"
    AGENT_TOOL_CALL = "agent_tool_call"
    CONFIG_OVERRIDE = "config_override"
    CLOCK_CHANGED = "clock_changed"
    SCENARIO_INJECTED = "scenario_injected"
    PHENOLOGY_GAP = "phenology_gap"


# Event kinds that close an EXECUTION_REQUESTED with the same idempotency key.
EXECUTION_CLOSING_KINDS: frozenset[EventKind] = frozenset(
    {EventKind.EXECUTION, EventKind.EXECUTION_FAILED}
)


class SensorKind(StrEnum):
    """Physical quantity a sensor measures."""

    SOIL_MOISTURE = "soil_moisture"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"


class CycleStatus(StrEnum):
    """Lifecycle of a crop cycle."""

    ACTIVE = "active"
    COMPLETED = "completed"
