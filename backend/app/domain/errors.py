"""Domain errors. The API layer maps them to HTTP status codes in one place."""


class DomainError(Exception):
    """Base class for expected, business-level failures."""


class NotFoundError(DomainError):
    """The requested entity does not exist."""

    def __init__(self, entity: str, entity_id: int) -> None:
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


class ConfigError(ValueError):
    """A configuration file is missing, malformed or unsafe. The app must not start."""
