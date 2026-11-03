"""The shopping assistant: one `shopper` run per question, bound to one customer (§4.16).

Its turns stay out of the farm's event log (market.md §7.4); the trace is
kept in memory for the run only.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.agent.llm.ports import LLMClient, LLMUnavailableError
from app.agent.loop import AgentLoop, RunStatus, Subagent
from app.agent.tools.registry import ToolRegistry
from app.agent.tools.shopper import ShopperSession, shopper_tools
from app.agent.trace import TraceEntry
from app.domain.models import JsonObject, JsonValue
from app.identity.models import Principal
from app.market.listings import GRAMS_PER_KG
from app.market.models import CartProposal, ProposalStatus
from app.market.orders import OrderService
from app.market.pricing import to_units
from app.market.recommend.service import RecommendationService
from app.market.store import ProductView, StoreService, require_customer
from app.market.trace.passport import PassportService
from app.simulator.clock import Clock


@dataclass(frozen=True)
class ShopperAnswer:
    run_id: str
    status: RunStatus
    answer: str | None
    proposal: CartProposal | None


class _PrivateTrace:
    """Customer conversations never reach the farm's event log (market.md §7.4)."""

    def __init__(self) -> None:
        self.entries: list[TraceEntry] = []

    def record(self, entry: TraceEntry) -> None:
        self.entries.append(entry)


def product_json(product: ProductView) -> dict[str, JsonValue]:
    """What the assistant reads about a product; the prices end in _cop (checked later)."""
    offer = product.offer
    return {
        "listing_id": product.listing_id,
        "crop": product.listing.crop,
        "crop_name": product.crop_name,
        "price_per_kg_cop": to_units(product.price.total_minor),
        "discount_pct": product.price.discount_pct,
        "offer_ends_on": None if offer is None else offer.ends_on.isoformat(),
        "available_kg": product.available_g // GRAMS_PER_KG,
        "harvested_on": product.harvested_on.isoformat(),
        "best_before": product.best_before.isoformat(),
        "producer": product.producer,
        "lot_code": product.listing.lot_code,
    }


class StoreShopperPort:
    """The market, scoped to one customer, as the tools see it."""

    def __init__(
        self,
        principal: Principal,
        store: StoreService,
        orders: OrderService,
        recommendations: RecommendationService,
        passports: PassportService,
        clock: Clock,
        run_id: str,
    ) -> None:
        self._principal = principal
        self._customer = require_customer(principal)
        self._store = store
        self._orders = orders
        self._recommendations = recommendations
        self._passports = passports
        self._clock = clock
        self._run_id = run_id

    def history(self, limit: int) -> JsonObject:
        orders: list[JsonValue] = [
            {
                "order_id": order.id,
                "placed_on": order.placed_at.date().isoformat(),
                "status": order.status.value,
                "lines": [
                    {
                        "crop_name": self._store.product_name(line.crop),
                        "quantity_kg": line.quantity_kg,
                        "unit_price_cop": to_units(line.price.total_minor),
                    }
                    for line in order.lines
                ],
            }
            for order in self._orders.history(self._principal)[:limit]
        ]
        return {"orders": orders}

    def recommendations(self, k: int) -> JsonObject:
        products: list[JsonValue] = [
            {
                **product_json(r.product),
                "reasons": [reason.value for reason in r.reasons],
                "evidence": dict(r.evidence),
                "suggested_kg": r.suggested_kg,
            }
            for r in self._recommendations.for_customer(self._principal, k)
        ]
        return {"products": products}

    def search(self, query: str) -> JsonObject:
        return {"products": [product_json(p) for p in self._store.catalogue(query)]}

    def offers_today(self) -> JsonObject:
        return {"offers": [product_json(p) for p in self._store.offers_today()]}

    def passport(self, lot_code: str) -> JsonObject:
        passport = self._passports.public(lot_code)
        journey: list[JsonValue] = [
            {"step": s.step, "on": s.on.isoformat(), "quantity_kg": s.quantity_kg, "place": s.place}
            for s in passport.journey
        ]
        return {
            "lot_code": passport.lot_code,
            "crop_name": passport.crop_name,
            "producer": passport.producer,
            "harvested_on": passport.harvested_on.isoformat(),
            "verified": passport.integrity.verified,
            "journey": journey,
        }

    def propose(self, items: Sequence[tuple[int, int]], note: str) -> JsonObject:
        """Checked like a cart line: an active product with the stock asked."""
        for listing_id, kg in items:
            product = self._store.product(listing_id)
            if product.available_g < kg * GRAMS_PER_KG:
                return {"error": f"only {product.available_g // GRAMS_PER_KG} kg of listing "
                                 f"{listing_id} are left"}  # fmt: skip
        proposal = self._store.add_proposal(
            CartProposal(
                customer_id=self._customer,
                items=tuple({"listing_id": i, "quantity_kg": kg} for i, kg in items),
                note=note,
                status=ProposalStatus.OPEN,
                created_at=self._clock.now(),
                run_id=self._run_id,
            )
        )
        return {"proposal_id": proposal.id, "status": "open, waiting for the customer"}


class ShopperService:
    def __init__(
        self,
        llm: LLMClient,
        subagent: Subagent,
        max_turns: int,
        port_for: Callable[[Principal, str], StoreShopperPort],
        new_id: Callable[[], str],
        proposal: Callable[[int], CartProposal],
    ) -> None:
        self._llm = llm
        self._subagent = subagent
        self._max_turns = max_turns
        self._port_for = port_for
        self._new_id = new_id
        self._proposal = proposal

    def ask(self, principal: Principal, question: str) -> ShopperAnswer:
        require_customer(principal)
        run_id = self._new_id()
        session = ShopperSession(self._port_for(principal, run_id))
        loop = AgentLoop(
            self._llm,
            ToolRegistry(shopper_tools(session)),
            _PrivateTrace(),
            [self._subagent],
            self._max_turns,
        )
        run = loop.run(self._subagent.name, question, run_id)
        if run.status is RunStatus.PAUSED:
            raise LLMUnavailableError("the shopping assistant's model did not answer")
        answer = run.output.get("answer") if isinstance(run.output, dict) else None
        proposal = None if session.proposal_id is None else self._proposal(session.proposal_id)
        return ShopperAnswer(run_id, run.status, answer if isinstance(answer, str) else None,
                             proposal)  # fmt: skip
