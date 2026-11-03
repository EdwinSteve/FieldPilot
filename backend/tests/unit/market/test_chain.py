"""One hash chain per lot (docs/market.md §4.3): any edit breaks it."""

from dataclasses import replace
from datetime import UTC, datetime

from app.market.trace.chain import canonical_json, link, verify_chain
from app.market.trace.models import GENESIS_HASH, BizStep, TraceEvent

T0 = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


def _chain(n: int = 3) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    previous = GENESIS_HASH
    for seq in range(n):
        event = link("FP-1-20261028-1", seq, BizStep.COMMISSIONING, T0, "farmer:7", 5000,
                     {"source_digest": "ab", "step": seq}, previous)  # fmt: skip
        events.append(event)
        previous = event.hash
    return events


def test_an_untouched_chain_verifies() -> None:
    assert verify_chain(_chain())


def test_an_empty_chain_proves_nothing() -> None:
    assert not verify_chain([])


def test_editing_any_field_of_any_event_breaks_the_chain() -> None:
    events = _chain()
    for index in range(len(events)):
        for change in ({"quantity_g": 4999}, {"actor": "farmer:8"}, {"data": {"step": 99}}):
            tampered = list(events)
            tampered[index] = replace(events[index], **change)
            assert not verify_chain(tampered), (index, change)


def test_removing_or_reordering_events_breaks_the_chain() -> None:
    events = _chain()
    assert not verify_chain(events[1:])
    assert not verify_chain([events[0], events[2], events[1]])


def test_canonical_json_does_not_depend_on_key_order() -> None:
    assert (
        canonical_json({"b": 1, "a": "ñ"})
        == canonical_json({"a": "ñ", "b": 1})
        == '{"a":"ñ","b":1}'
    )
