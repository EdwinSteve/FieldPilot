"""The shopping assistant's tools (architecture §4.16, D085).

Every tool is bound to one customer when the session is built; none takes a
customer id, so the model can only ever read that customer's data. The
model proposes a cart; only the customer's checkout buys.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.agent.scope import StoreTopic
from app.agent.tools.registry import Tool, ToolRefusedError
from app.domain.models import JsonObject, JsonValue

PRICE_TOLERANCE = 0.5  # pesos: a price written with rounding still matches
_AMOUNT = re.compile(r"(?:\$\s?|COP\s?)(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s?COP")


class ShopperPort(Protocol):
    """What the assistant may read and write, already scoped to one customer."""

    def history(self, limit: int) -> JsonObject: ...
    def recommendations(self, k: int) -> JsonObject: ...
    def search(self, query: str) -> JsonObject: ...
    def offers_today(self) -> JsonObject: ...
    def passport(self, lot_code: str) -> JsonObject: ...
    def propose(self, items: Sequence[tuple[int, int]], note: str) -> JsonObject: ...


@dataclass
class ShopperSession:
    """Per run: the prices the tools returned, so the answer can be checked against them."""

    port: ShopperPort
    prices: set[float] = field(default_factory=set)
    proposal_id: int | None = None

    def remember_prices(self, value: JsonValue) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key.endswith("_cop") and isinstance(item, int | float):
                    self.prices.add(float(item))
                else:
                    self.remember_prices(item)
        elif isinstance(value, list):
            for item in value:
                self.remember_prices(item)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HistoryInput(_Strict):
    limit: int = Field(default=10, ge=1, le=50, description="How many recent orders.")


class RecommendInput(_Strict):
    k: int = Field(default=5, ge=1, le=20, description="How many products.")


class SearchInput(_Strict):
    query: str = Field(min_length=1, max_length=60, description="A crop or product name.")


class NoInput(_Strict):
    pass


class PassportInput(_Strict):
    lot_code: str = Field(min_length=3, max_length=40, description="A lot code from a product.")


class CartLineInput(_Strict):
    listing_id: int = Field(gt=0)
    quantity_kg: int = Field(gt=0, le=100)


class ProposeInput(_Strict):
    items: list[CartLineInput] = Field(min_length=1, max_length=20)
    note: str = Field(min_length=1, max_length=400, description="Why, for the customer.")


class AnswerInput(_Strict):
    topic: StoreTopic = Field(
        description="What the question is about; out_of_scope for anything that is not the "
        "store's products, prices, cart, meals or origin (D088)."
    )
    text: str = Field(
        default="", description="The answer, in the customer's language; empty when out_of_scope."
    )


def shopper_tools(session: ShopperSession) -> list[Tool[Any]]:
    return [
        Tool(
            "get_purchase_history",
            "The customer's recent orders: products, kilograms and dates.",
            HistoryInput,
            _reading(session, lambda a: session.port.history(a.limit)),
        ),
        Tool(
            "get_recommendations",
            "Products ranked for this customer, each with reason codes and evidence.",
            RecommendInput,
            _reading(session, lambda a: session.port.recommendations(a.k)),
        ),
        Tool(
            "search_products",
            "Products in stock that match a crop or name, with the price per kg.",
            SearchInput,
            _reading(session, lambda a: session.port.search(a.query)),
        ),
        Tool(
            "get_offers_today",
            "Today's offers, validated now: dates, stock and the farmer's minimum share.",
            NoInput,
            _reading(session, lambda _a: session.port.offers_today()),
        ),
        Tool(
            "get_passport",
            "Where a lot comes from: harvest, warehouse and checks, without personal data.",
            PassportInput,
            _reading(session, lambda a: session.port.passport(a.lot_code)),
        ),
        Tool(
            "propose_cart",
            "Propose a cart. It does not buy: the customer sees it and accepts it or not.",
            ProposeInput,
            _propose(session),
            writes=True,
        ),
        Tool(
            "answer_customer",
            "Answer the customer. Closes the turn. Every price must come from a tool result. "
            "Off-topic questions: topic out_of_scope.",
            AnswerInput,
            _answer(session),
            closes_run=True,
        ),
    ]


def _reading[In: BaseModel](
    session: ShopperSession, read: Callable[[In], JsonObject]
) -> Callable[[In], JsonObject]:
    def handler(args: In) -> JsonObject:
        result = read(args)
        session.remember_prices(dict(result))
        return result

    return handler


def _propose(session: ShopperSession) -> Callable[[ProposeInput], JsonObject]:
    def handler(args: ProposeInput) -> JsonObject:
        items = [(line.listing_id, line.quantity_kg) for line in args.items]
        result = session.port.propose(items, args.note)
        proposal = result.get("proposal_id")
        session.proposal_id = proposal if isinstance(proposal, int) else None
        return result

    return handler


def _answer(session: ShopperSession) -> Callable[[AnswerInput], JsonObject]:
    def handler(args: AnswerInput) -> JsonObject:
        if args.topic is StoreTopic.OUT_OF_SCOPE:
            session.proposal_id = None  # no cart rides on a declined question
            return {"answer": None, "topic": args.topic.value, "proposal_id": None}
        if not args.text.strip():
            raise ToolRefusedError("Answer refused: the answer is empty.")
        unknown = [
            written
            for written, value in _amounts(args.text)
            if not any(abs(value - p) <= PRICE_TOLERANCE for p in session.prices)
        ]
        if unknown:
            raise ToolRefusedError(
                f"Answer refused: prices not returned by any tool: {unknown}. "
                "Use only the prices the tools gave you."
            )
        return {"answer": args.text, "topic": args.topic.value, "proposal_id": session.proposal_id}

    return handler


def _amounts(text: str) -> list[tuple[str, float]]:
    found = []
    for match in _AMOUNT.finditer(text):
        written = match.group(1) or match.group(2)
        found.append((match.group(0).strip(), float(written.replace(",", ""))))
    return found
