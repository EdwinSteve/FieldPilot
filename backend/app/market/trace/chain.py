"""One SHA-256 hash chain per lot (docs/market.md §4.3). Pure functions, no I/O."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime

from app.domain.models import JsonValue
from app.market.trace.models import GENESIS_HASH, BizStep, TraceEvent


def canonical_json(value: JsonValue) -> str:
    """Sorted keys, no spaces, UTF-8 kept: the same value always gives the same text."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: JsonValue) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def link(
    lot_code: str,
    seq: int,
    biz_step: BizStep,
    occurred_at: datetime,
    actor: str,
    quantity_g: int,
    data: Mapping[str, JsonValue],
    prev_hash: str,
) -> TraceEvent:
    """The next event of a chain, its hash covering the body and the previous hash."""
    body = _body(lot_code, seq, biz_step, occurred_at, actor, quantity_g, data)
    return TraceEvent(
        lot_code=lot_code,
        seq=seq,
        biz_step=biz_step,
        occurred_at=occurred_at,
        actor=actor,
        quantity_g=quantity_g,
        prev_hash=prev_hash,
        hash=_hash(prev_hash, body),
        data=data,
    )


def verify_chain(events: Sequence[TraceEvent]) -> bool:
    """Numbered from 0, each linked to the previous one, each hash recomputing."""
    previous = GENESIS_HASH
    for seq, event in enumerate(events):
        body = _body(
            event.lot_code, event.seq, event.biz_step, event.occurred_at, event.actor,
            event.quantity_g, event.data,
        )  # fmt: skip
        if event.seq != seq or event.prev_hash != previous:
            return False
        if event.hash != _hash(previous, body):
            return False
        previous = event.hash
    return bool(events)


def _body(
    lot_code: str,
    seq: int,
    biz_step: BizStep,
    occurred_at: datetime,
    actor: str,
    quantity_g: int,
    data: Mapping[str, JsonValue],
) -> JsonValue:
    return {
        "lot_code": lot_code,
        "seq": seq,
        "biz_step": biz_step.value,
        "occurred_at": occurred_at.isoformat(),
        "actor": actor,
        "quantity_g": quantity_g,
        "data": dict(data),
    }


def _hash(prev_hash: str, body: JsonValue) -> str:
    return hashlib.sha256((prev_hash + canonical_json(body)).encode("utf-8")).hexdigest()
