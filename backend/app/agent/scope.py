"""What each assistant may talk about (D088).

The closing tool takes one of these topics, so the model classifies every
answer. With OUT_OF_SCOPE the model's text is dropped and the service answers
with a fixed text: nothing the model writes off its subject reaches the user.
"""

from enum import StrEnum

OUT_OF_SCOPE = "out_of_scope"


class FarmTopic(StrEnum):
    """The farm chat: the crop of the plot and what it needs."""

    CROP = "crop"  # stage, degree-days, crop needs
    WATER = "water"  # soil moisture, irrigation
    WEATHER = "weather"  # forecast, rain, temperature
    FIELD = "field"  # zones and their readings
    TASKS = "tasks"  # pending or scheduled actions
    OUT_OF_SCOPE = OUT_OF_SCOPE


class StoreTopic(StrEnum):
    """The shopping assistant: the store's products."""

    PRODUCTS = "products"
    PRICES_OFFERS = "prices_offers"
    CART_ORDERS = "cart_orders"
    MEAL_PLANNING = "meal_planning"  # which products a dish needs
    ORIGIN = "origin"  # where a lot comes from (the passport)
    OUT_OF_SCOPE = OUT_OF_SCOPE


def is_out_of_scope(output: object) -> bool:
    """Whether a closing tool's output declined the question."""
    return isinstance(output, dict) and output.get("topic") == OUT_OF_SCOPE
