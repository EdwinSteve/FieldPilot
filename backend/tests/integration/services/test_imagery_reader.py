from collections.abc import Callable
from datetime import date

from app.domain.models import Plot, Zone
from app.persistence.unit_of_work import SqlUnitOfWork
from app.satellite.scenes import ImageryLoader
from app.satellite.segmentation import (
    Box,
    MockSegmentation,
    SegmentationProvider,
    SegmentationUnavailableError,
)
from app.services.imagery_reader import StoredImageryReader
from tests.conftest import SATELLITE_DIR, T0, FieldIds
from tests.integration.agent.session import IMAGING, SAM_BOXES

UowFactory = Callable[[], SqlUnitOfWork]
DAY = date(2026, 10, 28)


class DownSegmentation:
    def __init__(self) -> None:
        self.calls = 0

    def segment(self, image_png: bytes, prompt: str) -> tuple[Box, ...]:
        self.calls += 1
        raise SegmentationUnavailableError("InternalServerError (HTTP 503)")


def _reader(
    uow: UowFactory, segmentation: SegmentationProvider | None = None
) -> StoredImageryReader:
    return StoredImageryReader(
        uow,
        ImageryLoader.from_directory(SATELLITE_DIR),
        segmentation or MockSegmentation(SAM_BOXES),
        IMAGING,
    )


def test_zones_are_matched_by_name(uow: UowFactory, field: FieldIds) -> None:
    """The conftest field has "Zone 2"; the scene has "Zona 1" and "Zona 2"."""
    with uow() as u:
        zona_2 = u.zones.add(Zone(field.plot_id, "Zona 2", 0.5, 32.0, valve_id="v9"))
        u.commit()

    view = _reader(uow).imagery(field.plot_id, DAY)

    assert view is not None and view.scene_id == "neiva-2026-10-28" and view.synthetic
    [zone] = view.zones
    assert (zone.zone_id, zone.ndvi_mean, zone.low_ndvi_pct, zone.bare_soil_pct) == (
        zona_2.id,
        0.378,
        21.2,
        25.3,
    )


def test_a_plot_without_a_scene_gets_none(uow: UowFactory) -> None:
    with uow() as u:
        plot = u.plots.add(Plot("Far", 4.6, -74.1, 1.0, created_at=T0, utc_offset_hours=-5.0))
        u.commit()
    assert plot.id is not None

    assert _reader(uow).imagery(plot.id, DAY) is None


def test_the_scene_is_segmented_once(uow: UowFactory, field: FieldIds) -> None:
    mock = MockSegmentation(SAM_BOXES)
    reader = _reader(uow, mock)

    reader.imagery(field.plot_id, DAY)
    reader.imagery(field.plot_id, DAY)

    assert len(mock.calls) == 1
    assert mock.calls[0][1] == "brown patch"


def test_an_outage_leaves_bare_soil_unknown_and_is_retried(
    uow: UowFactory, field: FieldIds
) -> None:
    with uow() as u:
        u.zones.add(Zone(field.plot_id, "Zona 1", 0.5, 32.0, valve_id="v8"))
        u.commit()
    down = DownSegmentation()
    reader = _reader(uow, down)

    first = reader.imagery(field.plot_id, DAY)
    reader.imagery(field.plot_id, DAY)

    assert first is not None
    assert first.zones[0].bare_soil_pct is None
    assert first.zones[0].ndvi_mean == 0.802  # NDVI does not depend on SAM
    assert first.segmentation_note is not None and "HTTP 503" in first.segmentation_note
    assert down.calls == 2  # an outage is not cached
