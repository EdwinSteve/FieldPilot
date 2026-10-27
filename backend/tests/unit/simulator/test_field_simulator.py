from datetime import UTC, datetime, timedelta

import pytest

from app.domain.errors import NotFoundError, ValveError
from app.simulator.field import FieldSimulator, SensorNoise
from app.simulator.scenarios import DroughtScenario, HeavyRainScenario
from app.simulator.water_balance import SoilParams
from app.simulator.weather import BaseWeather

T0 = datetime(2026, 10, 27, 6, 0, tzinfo=UTC)
ZONE = 2
SOIL = SoilParams()
NO_ET = BaseWeather(et0_mm_per_day=0.0)
SILENT = SensorNoise(0.0, 0.0, 0.0)


def simulator(
    seed: int = 7, weather: BaseWeather | None = None, noise: SensorNoise | None = None
) -> FieldSimulator:
    sim = FieldSimulator(T0, weather=weather, seed=seed, noise=noise)
    sim.add_zone(ZONE, SOIL, initial_vwc=25.0)
    return sim


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


# --- valves (D007) --------------------------------------------------------


def test_closing_mid_run_returns_rate_times_elapsed_time() -> None:
    sim = simulator()
    sim.open(ZONE, target_mm=20.0, rate_mm_per_h=10.0, at=T0)

    applied = sim.close(ZONE, at(42))

    assert applied <= 20.0
    assert applied == 10.0 * (42 / 60)  # exact: rate x elapsed, not grid-rounded
    assert 20.0 - applied == pytest.approx(10.0 * (78 / 60))  # remaining time at the same rate


def test_applied_water_never_exceeds_target() -> None:
    sim = simulator()
    sim.open(ZONE, target_mm=5.0, rate_mm_per_h=10.0, at=T0)

    status = sim.status(ZONE, at(90))

    assert status.is_open is False
    assert status.applied_mm == 5.0


def test_closing_a_valve_that_already_finished_is_rejected() -> None:
    sim = simulator()
    sim.open(ZONE, target_mm=5.0, rate_mm_per_h=10.0, at=T0)

    with pytest.raises(ValveError, match="not open"):
        sim.close(ZONE, at(31))


def test_opening_an_open_valve_is_rejected() -> None:
    sim = simulator()
    sim.open(ZONE, target_mm=5.0, rate_mm_per_h=10.0, at=T0)

    with pytest.raises(ValveError, match="already open"):
        sim.open(ZONE, target_mm=5.0, rate_mm_per_h=10.0, at=at(10))


def test_closing_mid_run_puts_only_the_applied_water_in_the_soil() -> None:
    sim = simulator(weather=NO_ET, noise=SILENT)
    sim.open(ZONE, target_mm=20.0, rate_mm_per_h=10.0, at=at(7))  # off-grid on purpose
    applied = sim.close(ZONE, at(49))

    snapshot = sim.read(ZONE, at(24 * 60))

    expected = SOIL.vwc(SOIL.water_mm(25.0) + applied)
    assert snapshot.soil_moisture_vwc == pytest.approx(expected)


# --- determinism ----------------------------------------------------------


SETUP_MINUTE = 37  # off-grid on purpose; the simulator rejects any earlier time after this


def _run_irrigation_and_drought(sim: FieldSimulator) -> None:
    sim.open(ZONE, target_mm=15.0, rate_mm_per_h=6.0, at=at(SETUP_MINUTE))
    sim.inject(DroughtScenario(start=at(600), end=at(2 * 24 * 60)))


def test_same_seed_gives_identical_readings() -> None:
    first, second = simulator(seed=11), simulator(seed=11)
    _run_irrigation_and_drought(first)
    _run_irrigation_and_drought(second)

    moments = [at(m) for m in range(SETUP_MINUTE, 3 * 24 * 60, 97)]

    assert [first.read(ZONE, t) for t in moments] == [second.read(ZONE, t) for t in moments]


def test_one_advance_equals_many_irregular_advances() -> None:
    one_shot, stepped = simulator(), simulator()
    _run_irrigation_and_drought(one_shot)
    _run_irrigation_and_drought(stepped)
    end = at(3 * 24 * 60 + 5)

    one_shot.advance_to(end)
    for minutes in [SETUP_MINUTE, 44, 45, 46, 200, 201, 999, 2000, 3 * 24 * 60]:
        stepped.advance_to(at(minutes))
    stepped.advance_to(end)

    assert stepped.integrated_until == one_shot.integrated_until
    assert stepped.read(ZONE, end) == one_shot.read(ZONE, end)


def test_reading_twice_at_the_same_time_gives_the_same_values() -> None:
    sim = simulator()

    assert sim.read(ZONE, at(100)) == sim.read(ZONE, at(100))


def test_reading_history_does_not_change_later_values() -> None:
    curious, quiet = simulator(), simulator()
    for minutes in range(0, 600, 15):
        curious.read(ZONE, at(minutes))
    curious.inject(HeavyRainScenario(start=at(2000), end=at(2100)))  # future, not yet active

    assert curious.read(ZONE, at(600)) == quiet.read(ZONE, at(600))


def test_each_zone_gets_its_own_noise() -> None:
    sim = simulator()
    sim.add_zone(ZONE + 1, SOIL, initial_vwc=25.0)

    first, second = sim.read(ZONE, at(60)), sim.read(ZONE + 1, at(60))

    assert first.soil_moisture_vwc != second.soil_moisture_vwc


def test_different_seed_changes_noise_but_not_the_physical_state() -> None:
    first, second = simulator(seed=1), simulator(seed=2)

    first.advance_to(at(600))
    second.advance_to(at(600))

    assert first.read(ZONE, at(600)) != second.read(ZONE, at(600))
    assert first._zones[ZONE].vwc == second._zones[ZONE].vwc


def test_snapshot_is_taken_at_the_last_grid_point() -> None:
    snapshot = simulator().read(ZONE, at(22))

    assert snapshot.at == at(15)


# --- scenarios ------------------------------------------------------------


def test_drought_dries_the_soil_faster_than_the_baseline() -> None:
    baseline, drought = simulator(noise=SILENT), simulator(noise=SILENT)
    drought.inject(DroughtScenario(start=T0, end=at(2 * 24 * 60)))
    two_days = at(2 * 24 * 60)

    assert (
        drought.read(ZONE, two_days).soil_moisture_vwc
        < baseline.read(ZONE, two_days).soil_moisture_vwc
    )


def test_heavy_rain_wets_the_soil() -> None:
    sim = simulator(weather=NO_ET, noise=SILENT)
    sim.inject(HeavyRainScenario(start=T0, end=at(6 * 60), total_mm=12.0))

    assert sim.read(ZONE, at(6 * 60)).soil_moisture_vwc == pytest.approx(29.0)  # 25 + 12/300


def test_heavy_rain_total_does_not_depend_on_grid_alignment() -> None:
    sim = simulator(weather=NO_ET, noise=SILENT)
    sim.inject(HeavyRainScenario(start=at(7), end=at(7 + 100), total_mm=6.0))

    assert sim.read(ZONE, at(4 * 60)).soil_moisture_vwc == pytest.approx(27.0)


def test_active_scenarios_follow_the_window() -> None:
    sim = simulator()
    rain = HeavyRainScenario(start=at(60), end=at(120))
    sim.inject(rain)

    assert sim.active_scenarios(at(30)) == ()
    assert sim.active_scenarios(at(60)) == (rain,)
    assert sim.active_scenarios(at(120)) == ()


# --- time guards ----------------------------------------------------------


def test_time_cannot_go_backwards() -> None:
    sim = simulator()
    sim.read(ZONE, at(60))

    with pytest.raises(ValueError, match="backwards"):
        sim.read(ZONE, at(30))


def test_scenario_cannot_start_in_the_simulated_past() -> None:
    sim = simulator()
    sim.advance_to(at(60))

    with pytest.raises(ValueError, match="before the current"):
        sim.inject(HeavyRainScenario(start=at(30), end=at(90)))


def test_unknown_zone_raises_not_found() -> None:
    with pytest.raises(NotFoundError):
        simulator().read(99, T0)
