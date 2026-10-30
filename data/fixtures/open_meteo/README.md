# Open-Meteo forecast fixtures

Read by `FixtureForecast` (`backend/app/weather/fixture.py`, D047). Each
file has the shape of an Open-Meteo `/v1/forecast` response requested with
`hourly=precipitation&timezone=GMT`.

| File | Location | Covers (UTC) | Rain |
|---|---|---|---|
| `neiva.json` | 2.95, -75.30 (grid point nearest the demo farm in Neiva, Huila) | 2026-10-27 00:00 → 2026-11-10 23:00 | Dry, except one synthetic event on 2026-11-02, from 18:00 to 22:00 UTC (13:00–17:00 in Neiva), 12.0 mm in total |

The values are **synthetic**, not a recorded forecast. They are chosen so
the demo has dry days for irrigation (D009) and one day where the 5 mm
forecast limit holds an irrigation for approval. A plot more than 0.1°
from every fixture gets no forecast (`None`), and the gate holds the
action (D027).
