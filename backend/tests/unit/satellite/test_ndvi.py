import pytest

from app.satellite.ndvi import NdviStats, NormalizedBox, compute_ndvi, zone_ndvi

WHOLE = NormalizedBox(0, 0, 1, 1)


def test_ndvi_is_nir_minus_red_over_their_sum() -> None:
    ndvi = compute_ndvi(((0.05, 0.25),), ((0.45, 0.30),))

    assert ndvi[0][0] == pytest.approx(0.8)
    assert ndvi[0][1] == pytest.approx(0.0909, abs=1e-4)


def test_a_pixel_without_signal_has_no_ndvi() -> None:
    """D058: never a guessed value."""
    assert compute_ndvi(((0.0, 0.1),), ((0.0, 0.3),))[0][0] is None


def test_bands_of_different_shape_are_refused() -> None:
    with pytest.raises(ValueError, match="differ in shape"):
        compute_ndvi(((0.1, 0.1),), ((0.3,),))


def test_zone_stats_use_only_pixels_whose_centre_is_inside() -> None:
    ndvi = ((0.8, 0.8, 0.2, 0.2),)

    left = zone_ndvi(ndvi, NormalizedBox(0, 0, 0.5, 1), low_threshold=0.4)
    right = zone_ndvi(ndvi, NormalizedBox(0.5, 0, 1, 1), low_threshold=0.4)

    assert left == NdviStats(0.8, 0.0, 2)
    assert right == NdviStats(0.2, 100.0, 2)


def test_undefined_pixels_are_left_out_of_the_mean() -> None:
    stats = zone_ndvi(((0.6, None, 0.2),), WHOLE, low_threshold=0.4)

    assert stats == NdviStats(0.4, 50.0, 2)


def test_the_threshold_is_strict() -> None:
    assert zone_ndvi(((0.4,),), WHOLE, low_threshold=0.4).low_pct == 0.0


def test_a_zone_without_values_has_no_statistics() -> None:
    assert zone_ndvi(((None, None),), WHOLE, low_threshold=0.4) == NdviStats(None, None, 0)


@pytest.mark.parametrize(
    "box", [(0.5, 0, 0.5, 1), (0, 0, 1.2, 1), (-0.1, 0, 1, 1), (0, 0.6, 1, 0.5)]
)
def test_a_box_outside_the_unit_square_is_refused(box: tuple[float, float, float, float]) -> None:
    with pytest.raises(ValueError, match="not a box inside"):
        NormalizedBox(*box)


def test_a_pixel_belongs_where_its_centre_falls() -> None:
    """Centres at 0.125, 0.375, 0.625, 0.875: a box from 0.1 to 0.6 holds the first two."""
    stats = zone_ndvi(((0.1, 0.5, 0.9, 0.3),), NormalizedBox(0.1, 0, 0.6, 1), low_threshold=0.4)

    assert stats == NdviStats(0.3, 50.0, 2)
