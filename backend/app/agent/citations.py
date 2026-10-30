"""D050: every number the agent states traces to a ledger observation.

Only numbers written with a unit are checked ("21 %", "15 mm", "412,5 GDD").
Numbers without one ("3 zonas", "día 2") are not: a stated limit of the
check. A stored value is rounded to the precision the text writes, then
compared with a 0.05 tolerance, so 37.96 written as "38" passes and 37.4
written as "38" fails.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.agent.brief import ObservationLedger

TOLERANCE = 0.05
_EPSILON = 1e-9  # float noise, so 0.05 itself passes
UNITS = ("mm", "%", "°C", "GDD", "kg/ha")
_NUMBER_WITH_UNIT = re.compile(
    r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(" + "|".join(re.escape(u) for u in UNITS) + r")(?![\w/])"
)


@dataclass(frozen=True)
class Fact:
    """A number the agent may state: a cited observation, or its own proposal's value."""

    value: float
    unit: str


@dataclass(frozen=True)
class NumberClaim:
    text: str
    value: float
    decimals: int
    unit: str


def numbers_with_units(text: str) -> list[NumberClaim]:
    claims = []
    for match in _NUMBER_WITH_UNIT.finditer(text):
        written, unit = match.group(1), match.group(2)
        decimals = len(re.split(r"[.,]", written)[1]) if re.search(r"[.,]", written) else 0
        claims.append(NumberClaim(match.group(0), float(written.replace(",", ".")), decimals, unit))
    return claims


def claim_matches(stored: float, claim: NumberClaim) -> bool:
    return abs(round_half_up(stored, claim.decimals) - claim.value) <= TOLERANCE + _EPSILON


def round_half_up(value: float, decimals: int) -> float:
    """How a person rounds (D056): 20.5 -> 21. Python's round() would give 20 (to even)."""
    step = Decimal(1).scaleb(-decimals)
    return float(Decimal(str(value)).quantize(step, rounding=ROUND_HALF_UP))


def value_matches(stored: float, claimed: float) -> bool:
    """For structured fields such as moisture_pct: no rounding, the same tolerance."""
    return abs(stored - claimed) <= TOLERANCE + _EPSILON


def unsupported_numbers(text: str, facts: Iterable[Fact]) -> list[str]:
    """The claims in `text` that no fact of the same unit supports, as written."""
    known = list(facts)
    return [
        claim.text
        for claim in numbers_with_units(text)
        if not any(f.unit == claim.unit and claim_matches(f.value, claim) for f in known)
    ]


def cited_facts(ledger: ObservationLedger, cited: Sequence[str]) -> tuple[list[Fact], list[str]]:
    """Numeric facts of the cited observations, and the ids that are not in the ledger."""
    facts: list[Fact] = []
    missing: list[str] = []
    for observation_id in cited:
        observation = ledger.get(observation_id)
        if observation is None:
            missing.append(observation_id)
        elif isinstance(observation.value, int | float) and observation.unit:
            facts.append(Fact(float(observation.value), observation.unit))
    return facts, missing
