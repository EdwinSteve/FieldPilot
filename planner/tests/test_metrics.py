import numpy as np
import pytest

from fieldpilot_planner.metrics import (
    coverage,
    expected_calibration_error,
    ndcg_at_k,
    pinball,
    rank,
    spearman,
)


def test_pinball_is_zero_for_a_perfect_forecast() -> None:
    y = np.array([0.2, 0.5])
    assert pinball(np.repeat(y[:, None], 3, axis=1), y) == 0


def test_ndcg_rewards_the_right_order() -> None:
    relevance = np.array([[0.9, 0.1, 0.5, 0.3]])
    assert ndcg_at_k(relevance, relevance) == pytest.approx(1.0)
    assert ndcg_at_k(-relevance, relevance) < 0.6


def test_calibration_and_coverage() -> None:
    prob = np.array([0.0, 0.0, 1.0, 1.0])
    assert expected_calibration_error(prob, np.array([0.0, 0.0, 1.0, 1.0])) == 0
    assert coverage(np.zeros(4), np.ones(4), np.array([0.5, 0.2, 1.5, -1])) == 0.5


def test_rank_averages_ties_and_spearman() -> None:
    np.testing.assert_allclose(rank(np.array([3.0, 1.0, 3.0])), [1.5, 0.0, 1.5])
    a = np.arange(10.0)
    assert spearman(a, a**3) == pytest.approx(1.0)
    assert spearman(a, -a) == pytest.approx(-1.0)
