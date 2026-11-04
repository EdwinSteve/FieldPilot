"""D095: the forecast the gate reads, as the farmer's Today screen shows it."""

from fastapi.testclient import TestClient

from tests.integration.api.conftest import Farm


def test_the_weather_is_the_gates_forecast_with_its_source(client: TestClient, farm: Farm) -> None:
    weather = client.get(f"/plots/{farm.plot_id}/weather").json()

    assert weather["source"] == "open_meteo_fixture"
    assert (weather["latitude"], weather["longitude"]) == (2.95, -75.3)  # the fixture's grid
    assert len(weather["hours"]) == 48
    shown = sum(h["rain_mm"] for h in weather["hours"][:24])
    assert weather["rain_next_24h_mm"] is not None
    assert abs(weather["rain_next_24h_mm"] - shown) < 1e-6  # on the hour: the same 24 hours


def test_an_unknown_plot_is_not_found(client: TestClient, farm: Farm) -> None:
    unknown = client.get("/plots/999/weather")

    assert unknown.status_code == 404
