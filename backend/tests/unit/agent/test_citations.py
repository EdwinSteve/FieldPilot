import pytest

from app.agent.brief import Observation, ObservationKind, ObservationLedger
from app.agent.citations import (
    Fact,
    NumberClaim,
    cited_facts,
    numbers_with_units,
    unsupported_numbers,
    value_matches,
)


def test_a_value_rounded_to_the_written_precision_passes() -> None:
    """D050 required test: a stored 37.96 written as "38" passes."""
    assert unsupported_numbers("La humedad está en 38 %.", [Fact(37.96, "%")]) == []


def test_a_value_that_rounds_elsewhere_fails() -> None:
    """D050 required test: a stored 37.4 written as "38" fails."""
    assert unsupported_numbers("La humedad está en 38 %.", [Fact(37.4, "%")]) == ["38 %"]


def test_rounding_is_what_lets_a_whole_number_through() -> None:
    """21.47 is 0.47 from 21: only rounding to the written precision accepts "21 %"."""
    assert unsupported_numbers("Humedad del 21 %.", [Fact(21.47, "%")]) == []
    assert unsupported_numbers("Humedad del 21,0 %.", [Fact(21.47, "%")]) == ["21,0 %"]


def test_halves_round_up_as_a_person_reads_them() -> None:
    assert unsupported_numbers("21 %", [Fact(20.5, "%")]) == []
    assert unsupported_numbers("2,68 mm", [Fact(2.675, "mm")]) == []


def test_decimal_comma_and_written_decimals() -> None:
    assert unsupported_numbers("Llevamos 412,5 GDD.", [Fact(412.53, "GDD")]) == []
    assert unsupported_numbers("Llevamos 412,6 GDD.", [Fact(412.53, "GDD")]) == ["412,6 GDD"]


def test_the_tolerance_is_0_05_after_rounding() -> None:
    assert unsupported_numbers("21,15 %", [Fact(21.1, "%")]) == []
    assert unsupported_numbers("21,16 %", [Fact(21.1, "%")]) == ["21,16 %"]


def test_numbers_without_a_unit_are_not_checked() -> None:
    """D050: a stated limit; "3 zonas" and "día 2" pass without a fact."""
    assert unsupported_numbers("Revisé 3 zonas el día 2.", []) == []


def test_the_unit_must_match() -> None:
    assert unsupported_numbers("Faltan 21 mm.", [Fact(21.0, "%")]) == ["21 mm"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("15 mm", [NumberClaim("15 mm", 15.0, 0, "mm")]),
        ("21,5%", [NumberClaim("21,5%", 21.5, 1, "%")]),
        (
            "28 °C y 60 kg/ha",
            [NumberClaim("28 °C", 28.0, 0, "°C"), NumberClaim("60 kg/ha", 60.0, 0, "kg/ha")],
        ),
        ("zona2 mm", []),
        ("10 mmHg", []),
        ("a las 06:00", []),
    ],
)
def test_numbers_with_units_are_found(text: str, expected: list[NumberClaim]) -> None:
    assert numbers_with_units(text) == expected


def test_structured_values_use_the_tolerance_without_rounding() -> None:
    assert value_matches(21.0, 21.05)
    assert not value_matches(21.0, 21.06)


def test_cited_facts_skip_non_numbers_and_report_missing_ids() -> None:
    ledger = ObservationLedger()
    ledger.add(Observation("reading-1", ObservationKind.SOIL_MOISTURE, 2, 21.0, "%", None))
    ledger.add(Observation("stage-cycle-1", ObservationKind.STAGE, None, "v6", "", None))
    ledger.add(Observation("forecast-x", ObservationKind.RAIN_FORECAST, None, None, "mm", None))

    facts, missing = cited_facts(ledger, ["reading-1", "stage-cycle-1", "forecast-x", "reading-9"])

    assert facts == [Fact(21.0, "%")]
    assert missing == ["reading-9"]
