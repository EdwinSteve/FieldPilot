"""Payments (§4.15): one port; the mock approves every charge, idempotently by key."""

import hashlib
from dataclasses import dataclass
from typing import Protocol

from app.domain.models import Money


@dataclass(frozen=True)
class PaymentResult:
    approved: bool
    reference: str


class PaymentGateway(Protocol):
    def charge(self, order_ref: str, amount: Money, idempotency_key: str) -> PaymentResult: ...
    def refund(self, reference: str, amount: Money) -> None: ...


class MockPaymentGateway:
    """No money moves: the reference is derived from the key, so a retry gets the same one."""

    def charge(self, order_ref: str, amount: Money, idempotency_key: str) -> PaymentResult:
        digest = hashlib.sha256(f"{order_ref}:{idempotency_key}:{amount}".encode()).hexdigest()[:16]
        return PaymentResult(approved=True, reference=f"MOCK-{digest.upper()}")

    def refund(self, reference: str, amount: Money) -> None:
        """Nothing to return in the mock."""
