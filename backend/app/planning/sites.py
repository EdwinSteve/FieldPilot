"""Site snapshots stored as files, written by `make planner-site` (D081)."""

from pathlib import Path

from fieldpilot_planner.manifest import file_digest
from fieldpilot_planner.serving import SiteSnapshot

from app.domain.errors import MissingDataError
from app.planning.ports import SiteRecord


class FixtureSiteSource:
    """data/fixtures/planner/site_<plot_id>.json; the backend never downloads data."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def site(self, plot_id: int) -> SiteRecord:
        path = self._directory / f"site_{plot_id}.json"
        if not path.is_file():
            raise MissingDataError(
                f"La parcela {plot_id} no tiene datos de sitio para el planificador "
                f"(make planner-site PLOT={plot_id})."
            )
        snapshot = SiteSnapshot.from_json(path.read_text(encoding="utf-8"))
        return SiteRecord(snapshot, file_digest(path))  # the same on Windows and Linux
