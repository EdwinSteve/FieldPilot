"""The shelf price of a kilogram (D080): pure, in minor units."""

from app.market.config import MarketFees
from app.market.models import MINOR_PER_UNIT, PriceBreakdown


def shelf_price(
    farmer_price_minor: int, fees: MarketFees, currency: str, discount_pct: int = 0
) -> PriceBreakdown:
    """The discount comes off the farmer's price; logistics is fixed per kg."""
    farmer = round(farmer_price_minor * (100 - discount_pct) / 100)
    return PriceBreakdown(
        farmer_minor=farmer,
        logistics_minor=round(fees.logistics_per_kg * MINOR_PER_UNIT),
        platform_minor=round(farmer * fees.platform_pct / 100),
        discount_pct=discount_pct,
        currency=currency,
    )


def respects_share(price: PriceBreakdown, fees: MarketFees) -> bool:
    return price.farmer_minor > 0 and price.farmer_share_pct >= fees.min_farmer_share_pct


def to_units(minor: int) -> float:
    """Minor units to pesos for the API: 345000 -> 3450.0."""
    return minor / MINOR_PER_UNIT
