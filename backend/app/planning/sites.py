"""Site snapshots stored as files (D081, D083).

Committed fixtures (data/fixtures/planner) come first, then the snapshots the
backend built itself (data/planner/sites). The backend never downloads data
on a request.
"""

from collections.abc import Sequence
from pathlib import Path

from fieldpilot_planner.manifest import file_digest
from fieldpilot_planner.serving import SiteSnapshot

from app.domain.errors import MissingDataError
from app.domain.models import Plot
from app.planning.ports import SiteRecord

MAX_OFFSET_DEG = 0.01  # a snapshot serves a plot only at its own coordinates


class FileSiteSource:
    def __init__(self, directories: Sequence[Path]) -> None:
        self._directories = tuple(directories)

    def site(self, plot: Plot) -> SiteRecord:
        for directory in self._directories:
            path = directory / f"site_{plot.id}.json"
            if not path.is_file():
                continue
            snapshot = SiteSnapshot.from_json(path.read_text(encoding="utf-8"))
            if _matches(snapshot, plot):
                return SiteRecord(snapshot, file_digest(path))  # the same on any platform
        raise MissingDataError(
            f"Plot {plot.id} has no climate and soil data for the planner yet "
            f"(GET /plots/{plot.id}/site).",
            key="site_missing",
            params={"plot_id": plot.id or 0},
        )


def _matches(snapshot: SiteSnapshot, plot: Plot) -> bool:
    return (
        abs(snapshot.lat - plot.latitude) <= MAX_OFFSET_DEG
        and abs(snapshot.lon - plot.longitude) <= MAX_OFFSET_DEG
    )
