"""Colombian open data (datos.gov.co, Socrata): DIVIPOLA centroids and EVA crop statistics."""

import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from fieldpilot_planner.sources.http import CachedHttp, build_url

DIVIPOLA_URL = "https://www.datos.gov.co/resource/gdxc-w37w.json"
PAGE = 50_000


@dataclass(frozen=True)
class EvaDataset:
    url: str
    municipality: str
    crop: str
    year: str
    area: str
    harvested: str
    production: str


EVA_DATASETS = (
    EvaDataset(
        "https://www.datos.gov.co/resource/2pnw-mmge.json",
        "c_d_mun", "cultivo", "a_o", "rea_sembrada_ha", "rea_cosechada_ha", "producci_n_t",
    ),
    EvaDataset(
        "https://www.datos.gov.co/resource/uejq-wxrr.json",
        "c_digo_dane_municipio", "cultivo", "a_o", "rea_sembrada", "rea_cosechada", "producci_n",
    ),
)  # fmt: skip


@dataclass(frozen=True)
class Municipality:
    code: str  # DANE, 5 digits
    department: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class EvaRecord:
    municipality: str
    crop_name: str  # normalized: upper case, no accents
    year: int
    sown_ha: float
    harvested_ha: float
    production_t: float


def normalize(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper().strip()


def _number(text: str | None) -> float:
    if not text:
        return 0.0
    return float(text.replace(",", "."))


def _paged(http: CachedHttp, url: str, query: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    offset = 0
    while True:
        params = {**query, "$limit": str(PAGE), "$offset": str(offset)}
        if "$group" not in query:
            params["$order"] = ":id"  # stable paging needs an order
        page = http.get_json(build_url(url, params))
        rows.extend(page)
        if len(page) < PAGE:
            return rows
        offset += PAGE


def fetch_municipalities(http: CachedHttp) -> list[Municipality]:
    rows = _paged(http, DIVIPOLA_URL, {})
    return [
        Municipality(
            code=row["cod_mpio"],
            department=row["cod_dpto"],
            name=row["nom_mpio"],
            lat=_number(row["latitud"]),
            lon=_number(row["longitud"]),
        )
        for row in rows
        if row.get("latitud") and row.get("longitud")
    ]


def _crop_names(http: CachedHttp, dataset: EvaDataset, wanted: set[str]) -> list[str]:
    rows = _paged(http, dataset.url, {"$select": dataset.crop, "$group": dataset.crop})
    return sorted(
        r[dataset.crop]
        for r in rows
        if r.get(dataset.crop) and normalize(r[dataset.crop]) in wanted
    )


def _quoted(names: Iterable[str]) -> str:
    return ", ".join("'" + n.replace("'", "''") + "'" for n in names)


def fetch_eva(http: CachedHttp, crop_names: Sequence[str]) -> list[EvaRecord]:
    """Sown and harvested area and production per municipality, crop and year."""
    wanted = {normalize(n) for n in crop_names}
    records: list[EvaRecord] = []
    for ds in EVA_DATASETS:
        names = _crop_names(http, ds, wanted)
        if not names:
            continue
        query = {
            "$select": (
                f"{ds.municipality} as m, {ds.crop} as c, {ds.year} as y, "
                f"sum({ds.area}) as sown, sum({ds.harvested}) as harvested, "
                f"sum({ds.production}) as production"
            ),
            "$group": f"{ds.municipality}, {ds.crop}, {ds.year}",
            "$where": f"{ds.crop} in ({_quoted(names)})",
        }
        records.extend(
            EvaRecord(
                municipality=row["m"].zfill(5),
                crop_name=normalize(row["c"]),
                year=int(row["y"]),
                sown_ha=_number(row.get("sown")),
                harvested_ha=_number(row.get("harvested")),
                production_t=_number(row.get("production")),
            )
            for row in _paged(http, ds.url, query)
            if row.get("m") and row.get("y")
        )
    return records
