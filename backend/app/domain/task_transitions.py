"""Task lifecycle as a pure state machine."""

from collections.abc import Mapping

from app.domain.enums import TaskStatus
from app.domain.errors import InvalidTransitionError

# Statuses a task can be created in, depending on the gate outcome.
INITIAL_STATUSES: frozenset[TaskStatus] = frozenset(
    {TaskStatus.PENDING_APPROVAL, TaskStatus.SCHEDULED}
)

ALLOWED_TRANSITIONS: Mapping[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING_APPROVAL: frozenset(
        {TaskStatus.SCHEDULED, TaskStatus.REJECTED, TaskStatus.FAILED}
    ),
    TaskStatus.SCHEDULED: frozenset({TaskStatus.EXECUTED, TaskStatus.REVERTED, TaskStatus.FAILED}),
    # A running irrigation or a calendar shift can still be reverted (D007).
    TaskStatus.EXECUTED: frozenset({TaskStatus.REVERTED}),
    TaskStatus.REVERTED: frozenset(),
    TaskStatus.REJECTED: frozenset(),
    TaskStatus.FAILED: frozenset(),
}


def is_terminal(status: TaskStatus) -> bool:
    """Return True if no transition leaves `status`."""
    return not ALLOWED_TRANSITIONS[status]


def ensure_transition_allowed(current: TaskStatus, target: TaskStatus) -> None:
    """Raise `InvalidTransitionError` unless `current -> target` is allowed."""
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(f"task cannot go from {current} to {target}")


def ensure_initial_status(status: TaskStatus) -> None:
    """Raise `InvalidTransitionError` unless a task may be created in `status`."""
    if status not in INITIAL_STATUSES:
        raise InvalidTransitionError(f"task cannot be created as {status}")
