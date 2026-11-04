"""The assistant in the cart (D087): one suggestion, from the recommender, in words.

No model is involved: the text is a template for the reason that adds most to
the score, so it is instant, deterministic and works in demo mode. The
customer acts on it through the cart's own endpoint.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.autonomy.messages import MessageCatalog
from app.identity.models import Principal
from app.market.listings import GRAMS_PER_KG
from app.market.models import DiscountSource
from app.market.recommend.scorers import ReasonCode, Recommendation
from app.market.recommend.service import RecommendationService
from app.market.store import StoreService

# Which template speaks for each lead reason; a deal names how it fits.
_TEMPLATES = {
    ReasonCode.REPURCHASE_DUE: "suggest_repurchase_due",
    ReasonCode.BOUGHT_TOGETHER: "suggest_bought_together",
    ReasonCode.ON_OFFER: "suggest_on_offer",
    ReasonCode.FRESH_HARVEST: "suggest_fresh_harvest",
    ReasonCode.POPULAR: "suggest_popular",
}


class ActionKind(StrEnum):
    ADD_TO_CART = "add_to_cart"  # PUT /store/cart/items/{listing_id}
    BETTER_DEAL = "better_deal"  # GET /store/cart/suggestion?prefer=deal&exclude=…


@dataclass(frozen=True)
class SuggestionAction:
    kind: ActionKind
    label: str
    listing_id: int | None = None
    quantity_kg: int | None = None
    exclude: tuple[int, ...] = ()


@dataclass(frozen=True)
class CartSuggestion:
    message: str
    recommendation: Recommendation | None  # None: the default answer
    actions: tuple[SuggestionAction, ...]


class CartSuggestionService:
    def __init__(
        self,
        recommendations: RecommendationService,
        store: StoreService,
        messages: MessageCatalog,
    ) -> None:
        self._recommendations = recommendations
        self._store = store
        self._messages = messages

    def suggest(
        self, principal: Principal, prefer_deal: bool = False, exclude: Collection[int] = ()
    ) -> CartSuggestion:
        """The best product the cart does not have yet; `prefer_deal` keeps discounts only."""
        cart = self._store.cart(principal)
        in_cart = frozenset(line.crop for line in cart.lines)
        candidates = [
            p
            for p in self._store.catalogue()
            if p.listing.crop not in in_cart
            and p.listing_id not in exclude
            and (not prefer_deal or p.offer is not None)
        ]
        ranked = self._recommendations.rank(principal, candidates, in_cart or None)
        if not ranked:
            fallback = "suggest_no_better_deal" if prefer_deal else "suggest_none"
            return CartSuggestion(self._messages.label(fallback), None, ())
        best = ranked[0]
        names = sorted({line.crop_name.lower() for line in cart.lines})
        return self._worded(best, names, tuple(sorted({*exclude, best.product.listing_id})))

    def _worded(
        self, best: Recommendation, cart_names: list[str], shown: tuple[int, ...]
    ) -> CartSuggestion:
        product = best.product
        kg = max(1, min(best.suggested_kg, product.available_g // GRAMS_PER_KG))
        crop = product.crop_name.lower()
        intro = (
            self._messages.label("cart_intro", cart=", ".join(cart_names))
            if cart_names
            else self._messages.label("cart_intro_empty")
        )
        actions = (
            SuggestionAction(ActionKind.ADD_TO_CART,
                             self._messages.label("suggest_add", kg=str(kg), crop=crop),
                             listing_id=product.listing_id, quantity_kg=kg),
            SuggestionAction(ActionKind.BETTER_DEAL, self._messages.label("suggest_better_deal"),
                             exclude=shown),
        )  # fmt: skip
        return CartSuggestion(f"{intro} {self._sentence(best, crop)}", best, actions)

    def _sentence(self, best: Recommendation, crop: str) -> str:
        product, evidence = best.product, best.evidence
        params = {"crop": crop, "Crop": product.crop_name}
        if product.offer is not None:
            params["pct"] = str(product.offer.discount_pct)
        today = self._store.today()
        if best.lead is ReasonCode.DEAL_FOR_YOU:
            key = f"suggest_deal_{evidence.get('link')}"
        else:
            key = _TEMPLATES.get(best.lead or ReasonCode.POPULAR, "suggest_popular")
        if best.lead is ReasonCode.REPURCHASE_DUE:
            params["ago"] = self._ago(today, date.fromisoformat(str(evidence["last_bought"])))
        if best.lead is ReasonCode.FRESH_HARVEST:
            params["ago"] = self._ago(today, product.harvested_on)
        sentence = self._messages.label(key, **params)
        clearance = product.offer is not None and product.offer.source is DiscountSource.CLEARANCE
        if clearance and best.lead in {ReasonCode.DEAL_FOR_YOU, ReasonCode.ON_OFFER}:
            days = str(max(1, product.days_left))
            sentence += " " + self._messages.label("suggest_clearance_note", days=days)
        return sentence

    def _ago(self, today: date, day: date) -> str:
        """How long ago, as people say it: "yesterday", "a week ago"."""
        key, n = ago_key((today - day).days)
        return self._messages.label(key, n=str(n))


def ago_key(days: int) -> tuple[str, int]:
    """The message key for `days` ago, and the number it shows."""
    if days <= 0:
        return "ago_today", 0
    if days == 1:
        return "ago_yesterday", 1
    if days < 7:
        return "ago_days", days
    if days < 14:
        return "ago_week", 1
    if days < 30:
        return "ago_weeks", days // 7
    return ("ago_month", 1) if days < 60 else ("ago_months", days // 30)
