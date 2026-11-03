"""Domain errors. The API layer maps them to HTTP status codes in one place."""


class DomainError(Exception):
    """Base class for expected, business-level failures."""


class NotFoundError(DomainError):
    """The requested entity does not exist."""

    def __init__(self, entity: str, entity_id: int | str) -> None:
        super().__init__(f"{entity} {entity_id} not found")
        self.entity = entity
        self.entity_id = entity_id


class InvalidTransitionError(DomainError):
    """A state change that the lifecycle does not allow."""


class MissingDataError(DomainError):
    """Required measurements are absent. The system never invents them (D019)."""


class DayNotFinishedError(DomainError):
    """A daily computation was requested before that local day ended."""


class ValveError(DomainError):
    """A valve command that does not match the valve's current state."""


class EmergencyStopActiveError(DomainError):
    """A command that adds water was refused because the emergency stop is active (D022)."""


class UnsupportedActionError(DomainError):
    """The actuator has no command for this action type (D005, D034)."""


class PermitMismatchError(DomainError):
    """The execution permit does not match the task it was presented with (D037)."""


class ConfigError(ValueError):
    """A configuration file is missing, malformed or unsafe. The app must not start."""


class ScenarioRejectedError(DomainError):
    """A scenario the simulator cannot apply, such as one starting in the simulated past."""


class ActiveCycleExistsError(DomainError):
    """A plot has one active cycle at a time (D083)."""


class InvalidSowingDateError(DomainError):
    """A sowing is confirmed after it happened: today or up to 60 days back (D083)."""


class OwnRiskRequiredError(DomainError):
    """The crop is outside the planner's top 3: the farmer must accept the risk (D083)."""


class InvalidHarvestError(DomainError):
    """A harvest date or quantity that cannot be true (D083)."""


class OpenTasksError(DomainError):
    """Tasks still pending or scheduled: nothing may act on a harvested field (D083)."""


class SiteJobPendingError(DomainError):
    """The plot's site data is already being built."""
