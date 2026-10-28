import pytest

from app.domain.units import pct_of_field_capacity


@pytest.mark.parametrize(
    ("vwc", "field_capacity", "expected"),
    [
        (34.0, 40.0, 85.0),
        (32.0, 32.0, 100.0),
        (21.0, 32.0, 65.625),
        (0.0, 32.0, 0.0),
    ],
)
def test_percent_of_field_capacity(vwc: float, field_capacity: float, expected: float) -> None:
    assert pct_of_field_capacity(vwc, field_capacity) == pytest.approx(expected)


def test_raw_reading_and_percent_differ() -> None:
    # The reason D015 exists: 30 looks safe against 85, but it is 93.75 % of capacity.
    assert pct_of_field_capacity(30.0, 32.0) == pytest.approx(93.75)


@pytest.mark.parametrize("field_capacity", [0.0, -5.0])
def test_non_positive_field_capacity_is_rejected(field_capacity: float) -> None:
    with pytest.raises(ValueError, match="positive"):
        pct_of_field_capacity(20.0, field_capacity)
