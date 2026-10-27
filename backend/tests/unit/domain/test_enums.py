from itertools import product

import pytest

from app.domain.enums import AutonomyLevel, strictest

A, N, P = AutonomyLevel.AUTONOMOUS, AutonomyLevel.NOTIFY, AutonomyLevel.APPROVAL
ORDER = [A, N, P]


@pytest.mark.parametrize(("left", "right"), list(product(ORDER, ORDER)))
def test_strictest_of_every_pair_is_the_higher_level(
    left: AutonomyLevel, right: AutonomyLevel
) -> None:
    expected = ORDER[max(ORDER.index(left), ORDER.index(right))]

    assert strictest(left, right) is expected
    assert strictest(right, left) is expected


def test_strictest_of_a_single_level_is_itself() -> None:
    assert strictest(N) is N


def test_approval_wins_over_any_combination() -> None:
    assert strictest(A, N, P, A) is P
