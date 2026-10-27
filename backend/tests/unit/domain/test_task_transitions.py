from itertools import product

import pytest

from app.domain.enums import TaskStatus
from app.domain.errors import InvalidTransitionError
from app.domain.task_transitions import (
    ALLOWED_TRANSITIONS,
    ensure_initial_status,
    ensure_transition_allowed,
    is_terminal,
)

S = TaskStatus
EXPECTED_ALLOWED = {
    (S.PENDING_APPROVAL, S.SCHEDULED),
    (S.PENDING_APPROVAL, S.REJECTED),
    (S.PENDING_APPROVAL, S.FAILED),
    (S.SCHEDULED, S.EXECUTED),
    (S.SCHEDULED, S.REVERTED),
    (S.SCHEDULED, S.FAILED),
    (S.EXECUTED, S.REVERTED),
}


def test_every_status_has_an_entry() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(TaskStatus)


@pytest.mark.parametrize(("current", "target"), list(product(TaskStatus, TaskStatus)))
def test_transition_matrix(current: TaskStatus, target: TaskStatus) -> None:
    if (current, target) in EXPECTED_ALLOWED:
        ensure_transition_allowed(current, target)
    else:
        with pytest.raises(InvalidTransitionError):
            ensure_transition_allowed(current, target)


def test_pending_approval_can_never_execute_directly() -> None:
    with pytest.raises(InvalidTransitionError):
        ensure_transition_allowed(S.PENDING_APPROVAL, S.EXECUTED)


@pytest.mark.parametrize("status", [S.REVERTED, S.REJECTED, S.FAILED])
def test_terminal_statuses(status: TaskStatus) -> None:
    assert is_terminal(status)


@pytest.mark.parametrize("status", [S.PENDING_APPROVAL, S.SCHEDULED])
def test_tasks_can_be_created_pending_or_scheduled(status: TaskStatus) -> None:
    ensure_initial_status(status)


@pytest.mark.parametrize("status", [S.EXECUTED, S.REVERTED, S.REJECTED, S.FAILED])
def test_tasks_cannot_be_created_in_a_later_status(status: TaskStatus) -> None:
    with pytest.raises(InvalidTransitionError):
        ensure_initial_status(status)
