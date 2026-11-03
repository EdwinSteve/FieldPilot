"""Market errors. English here; the catalogue translates them by key (D084, D085)."""

from app.domain.errors import DomainError


class PriceTooLowError(DomainError):
    """The farmer's share would fall under the minimum (D080)."""


class ListingStateError(DomainError):
    """The listing's state does not allow this now."""


class InvalidOfferError(DomainError):
    """An offer outside the allowed discount or dates."""


class InvalidReceiptError(DomainError):
    """A receipt above what was dispatched, or of nothing."""


class OutOfStockError(DomainError):
    """Not enough stock for what was asked."""


class EmptyCartError(DomainError):
    """Checkout of an empty cart."""


class PaymentDeclinedError(DomainError):
    """The payment gateway refused the charge."""
