"""Implements the agent's `ImageryReader`: NDVI and bare soil per zone (D058-D060, D077)."""

from collections.abc import Callable
from datetime import date

from app.agent.field import ImageryView, ZoneImagery
from app.persistence.ports import UnitOfWork
from app.phenology.catalog import CropCatalog
from app.satellite.config import ImagingConfig
from app.satellite.ndvi import compute_ndvi, zone_ndvi
from app.satellite.scenes import ImageryLoader, Scene
from app.satellite.segmentation import (
    Box,
    SegmentationProvider,
    SegmentationUnavailableError,
    covered_pct,
)
from app.services.gate_context import active_cycle

UowFactory = Callable[[], UnitOfWork]


class StoredImageryReader:
    """Matches scene zones to stored zones by name. Segments each scene once.

    Low vigour is judged with the threshold of the plot's crop (D077).
    """

    def __init__(
        self,
        uow: UowFactory,
        loader: ImageryLoader,
        segmentation: SegmentationProvider,
        config: ImagingConfig,
        crops: CropCatalog,
    ) -> None:
        self._uow = uow
        self._loader = loader
        self._segmentation = segmentation
        self._config = config
        self._crops = crops
        self._boxes: dict[str, tuple[Box, ...]] = {}

    def imagery(self, plot_id: int, day: date) -> ImageryView | None:
        with self._uow() as u:
            plot = u.plots.get(plot_id)
            zones = list(u.zones.list_by_plot(plot_id))
        scene = self._loader.latest(plot.latitude, plot.longitude, day)
        if scene is None:
            return None
        threshold = self._threshold(plot_id)
        boxes, note = self._segment(scene)
        ndvi = compute_ndvi(scene.red, scene.nir)
        views = []
        for zone in zones:
            area = scene.zones.get(zone.name)
            if area is None or zone.id is None:
                continue
            stats = zone_ndvi(ndvi, area, threshold)
            bare = None if boxes is None else covered_pct(boxes, area)
            views.append(
                ZoneImagery(
                    zone.id, stats.mean, stats.low_pct, bare, (area.x1, area.y1, area.x2, area.y2)
                )
            )
        return ImageryView(
            scene.scene_id,
            scene.acquired_on,
            scene.synthetic,
            threshold,
            tuple(views),
            note,
            () if boxes is None else tuple(box.normalized() for box in boxes),
        )

    def _threshold(self, plot_id: int) -> float:
        """The low-NDVI threshold of the plot's active crop; no cycle means no crop to judge."""
        with self._uow() as u:
            cycle = active_cycle(u, plot_id)
        return self._crops[cycle.crop].low_ndvi_threshold

    def scene_png(self, plot_id: int, day: date) -> bytes | None:
        """The scene's RGB image for the dashboard overlay; None when there is no scene."""
        with self._uow() as u:
            plot = u.plots.get(plot_id)
        scene = self._loader.latest(plot.latitude, plot.longitude, day)
        return None if scene is None else scene.rgb_png()

    def _segment(self, scene: Scene) -> tuple[tuple[Box, ...] | None, str | None]:
        """The scene's boxes, or None with the reason. An outage is not cached."""
        if scene.scene_id not in self._boxes:
            try:
                prompt = self._config.segmentation_prompt
                self._boxes[scene.scene_id] = self._segmentation.segment(scene.rgb_png(), prompt)
            except SegmentationUnavailableError as exc:
                return None, f"Segmentation unavailable ({exc}); bare soil is unknown."
        return self._boxes[scene.scene_id], None
