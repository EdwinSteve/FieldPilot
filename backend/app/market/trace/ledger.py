"""Append an event to a lot's hash chain, inside the caller's unit of work (D085)."""

from collections.abc import Mapping
from datetime import datetime

from app.domain.models import JsonValue
from app.market.trace.chain import link
from app.market.trace.models import GENESIS_HASH, BizStep, TraceEvent
from app.persistence.ports import UnitOfWork


def append_trace(
    uow: UnitOfWork,
    lot_code: str,
    biz_step: BizStep,
    at: datetime,
    actor: str,
    quantity_g: int,
    data: Mapping[str, JsonValue],
) -> TraceEvent:
    """The next event of the chain: seq and previous hash come from its head."""
    chain = uow.trace_events.list(lot_code)
    previous = chain[-1].hash if chain else GENESIS_HASH
    event = link(lot_code, len(chain), biz_step, at, actor, quantity_g, data, previous)
    return uow.trace_events.append(event)
