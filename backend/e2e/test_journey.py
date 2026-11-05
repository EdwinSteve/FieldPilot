"""FieldPilot from the first plan to the last sale, over HTTP, as one farmer's season.

The stages run in order and share one `Journey`, as a real season does: a
failure stops the rest, and its message says which step broke.

1. Plan and sow: a farmer registers, creates a plot, reads the planner's
   recommendation and confirms the sowing.
2. Automate: the demo plot's sensors report, the daily cycle (monitoring,
   imaging, irrigation, reporting) assesses and irrigates, and the chat
   answers only about the crop.
3. Sell: the harvest becomes a lot with a passport, goes through the Bogotá
   warehouse, the shopping assistant proposes a cart, the customer pays, the
   operator delivers, the farmer is paid and the passport shows the sale.
   Near its best-before day the product is marked down by itself.

`make e2e` plays the agents with the fake Muse and checks every step exactly.
`make e2e-live` runs the same season against the real Muse: what the backend
guarantees is still checked exactly, while what is the model's judgement (how
many irrigations, the words of an answer) is reported, not required. The last
step prints the model's report card from the agent trace.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import httpx2
import pytest

from e2e.conftest import PASSWORD, Stack

FARMER, CUSTOMER, OPERATOR = "3001234567", "3157654321", "3201112233"
NEIVA = {  # the coordinates of the shipped planner site (data/fixtures/planner/site_1.json)
    "name": "Finca La Esperanza",
    "municipality": "Neiva",
    "department": "Huila",
    "latitude": 2.93,
    "longitude": -75.28,
    "area_ha": 2.0,
}
HOUR, DAY = 3600, 86_400
OPEN = {"pending_approval", "scheduled"}
COLOMBIA_UTC_OFFSET_HOURS = -5  # the journey's plot is in Colombia
WATER = ("irrigation", "extra_irrigation", "stop_irrigation")
FARM_TOPICS = {"crop", "water", "weather", "field", "tasks"}
STORE_TOPICS = {"products", "prices_offers", "cart_orders", "meal_planning", "origin"}


@dataclass
class Journey:
    stack: Stack
    tokens: dict[str, dict[str, str]] = field(default_factory=dict)
    plot_id: int = 0
    cycle_id: int = 0
    zones: dict[str, int] = field(default_factory=dict)  # name -> id
    lot_code: str = ""
    listing_id: int = 0
    notes: list[str] = field(default_factory=list)  # what the model did, for the report

    @property
    def live(self) -> bool:
        return self.stack.live

    @property
    def api(self) -> httpx2.Client:
        return self.stack.api

    def call(self, method: str, path: str, who: str | None = None, **kwargs: Any) -> Any:
        """One request; anything but 2xx fails with the backend's own answer."""
        headers = self.tokens.get(who, {}) if who else {}
        response = self.api.request(method, path, headers=headers, **kwargs)
        assert response.is_success, f"{method} {path} -> {response.status_code}: {response.text}"
        return response.json() if response.content else None

    def register(self, phone: str, role: str) -> None:
        policy = self.call("GET", "/auth/privacy-policy")["version"]
        body = {"phone": phone, "full_name": f"E2E {role}", "password": PASSWORD, "role": role,
                "accept_privacy_policy": True, "privacy_policy_version": policy}  # fmt: skip
        tokens = self.call("POST", "/auth/register", json=body)["tokens"]
        self.tokens[role] = {"Authorization": f"Bearer {tokens['access_token']}"}

    def login(self, phone: str, role: str) -> None:
        tokens = self.call("POST", "/auth/login", json={"phone": phone, "password": PASSWORD})
        self.tokens[role] = {"Authorization": f"Bearer {tokens['access_token']}"}

    def advance(self, seconds: int, tick: bool = True) -> Any:
        """Move the simulated clock; a tick records the sensors and runs due tasks."""
        self.call(
            "POST", "/clock", "farmer", json={"action": "advance", "advance_seconds": seconds}
        )
        return self.call("POST", "/simulation/tick", "farmer") if tick else None

    def moisture(self, zone: str) -> float:
        sensors = self.call("GET", f"/readings?zone_id={self.zones[zone]}", "farmer")
        [moisture] = [s for s in sensors if s["kind"] == "soil_moisture"]
        return float(moisture["readings"][-1]["value"])

    def today(self) -> date:
        """The plot's local day (D018): the backend judges dates by it, never by UTC."""
        now = datetime.fromisoformat(self.call("GET", "/clock", "farmer")["now"])
        return (now + timedelta(hours=COLOMBIA_UTC_OFFSET_HOURS)).date()


@pytest.fixture(scope="module")
def journey(stack: Stack) -> Journey:
    return Journey(stack)


# --- stage 1: plan and sow -----------------------------------------------------------------


def test_1_a_farmer_follows_the_planners_recommendation(journey: Journey) -> None:
    journey.register(FARMER, "farmer")

    plot = journey.call("POST", "/plots", "farmer", json=NEIVA)
    journey.plot_id = plot["id"]
    site = journey.call("GET", f"/plots/{journey.plot_id}/site", "farmer")
    plan = journey.call("GET", f"/plots/{journey.plot_id}/planting-plan?weeks=1", "farmer")

    assert site["status"] == "ready", site
    assert plan["model"].startswith("planner-"), "the trained network serves, not the fallback"
    week = plan["weeks"][0]
    outlooks = week["outlooks"]
    best_first = sorted(outlooks, key=lambda o: (-o["rel_yield_p50"], -o["p_success"]))
    assert len(outlooks) >= 3 and outlooks == best_first
    recommended = [outlook["crop"] for outlook in outlooks[:3]]

    # Maize is the crop stage 2 automates; sowing outside the top 3 needs the farmer's risk.
    sowing = {"crop": "maize", "sowing_date": week["sowing_date"], "accept_own_risk": False}
    first = journey.api.post(f"/plots/{journey.plot_id}/cycles", json=sowing,
                             headers=journey.tokens["farmer"])  # fmt: skip
    if "maize" in recommended:
        assert first.status_code == 201, first.text
        cycle = first.json()
        assert cycle["plan"]["rank"] == recommended.index("maize") + 1
    else:
        assert first.json()["error"] == "OwnRiskRequiredError", first.text
        cycle = journey.call("POST", f"/plots/{journey.plot_id}/cycles", "farmer",
                             json=sowing | {"accept_own_risk": True})  # fmt: skip
        assert cycle["own_risk"] is True
    assert (cycle["status"], cycle["automated"]) == ("active", True)
    journey.cycle_id = cycle["id"]


# --- stage 2: the crop runs itself ---------------------------------------------------------


def test_2_the_demo_sensors_report_from_the_first_tick(journey: Journey) -> None:
    zones = journey.call("GET", f"/plots/{journey.plot_id}/zones", "farmer")
    journey.zones = {zone["name"]: zone["id"] for zone in zones}

    tick = journey.advance(HOUR)

    assert set(journey.zones) == {"Zone 1", "Zone 2"}
    assert tick["zones_without_data"] == [] and tick["readings_recorded"] >= 6
    assert journey.moisture("Zone 2") < journey.moisture("Zone 1")  # the kit's dry zone


def test_3_the_daily_cycle_assesses_and_irrigates_the_dry_zone(journey: Journey) -> None:
    dry_before = journey.moisture("Zone 2")

    cycle = journey.call("POST", "/agent/daily-cycle", "farmer", json={"plot_id": journey.plot_id})

    assert cycle["status"] == "completed", cycle
    runs = [run["subagent"] for run in cycle["runs"]]
    assert runs[-1] == "agronomist" and "monitoring" in runs  # D093: the agronomist leads
    journey.notes.append(f"daily cycle: the agronomist consulted {runs[:-1]}")
    brief = cycle["brief"]
    statuses = {z["zone_id"]: z["status"] for z in brief["assessment"]["zones"]}
    assert set(statuses) == set(journey.zones.values())  # the backend checks every zone
    assert brief["report_id"] is not None  # the day cannot close without the report
    proposals = brief["proposals"]
    water = [p for p in proposals if p["action_type"] in WATER]
    tasks = [p for p in proposals if p["action_type"] not in WATER]
    agronomist_tasks = [(p["action_type"], p["status"]) for p in tasks]
    journey.notes.append(f"daily cycle: zones {statuses}, {len(water)} irrigation(s), "
                         f"agronomist tasks {agronomist_tasks}")  # fmt: skip
    for task in tasks:  # D005: inputs always wait for the farmer
        if task["action_type"] in ("fertilizer", "agrochemical"):
            assert task["status"] == "pending_approval", task
    if not journey.live:
        assert runs == ["monitoring", "imaging", "crop_health", "soil_nutrition", "irrigation",
                        "reporting", "agronomist"]  # fmt: skip
        assert len(brief["imaging"]["zones"]) == 2  # the synthetic scene covers both
        assert statuses == {journey.zones["Zone 1"]: "ok", journey.zones["Zone 2"]: "dry"}
        assert [p["zone_id"] for p in water] == [journey.zones["Zone 2"]]
        nutrition = {z["zone_id"]: z["deficits"] for z in brief["nutrition"]}
        assert "nitrogen" in nutrition[journey.zones["Zone 2"]]  # the probe's poor zone
        assert ("fertilizer", journey.zones["Zone 2"]) in {
            (p["action_type"], p["zone_id"]) for p in tasks
        }

    _settle_tasks(journey, [p["task_id"] for p in water])
    _do_manual_tasks(journey, [p["task_id"] for p in tasks])
    journey.advance(HOUR)  # a reading taken after the irrigation
    statuses_now = [_task(journey, p["task_id"])["status"] for p in proposals]
    journey.notes.append(f"proposed tasks ended as {statuses_now}")
    if not journey.live:
        assert set(statuses_now) == {"executed"}
        assert journey.moisture("Zone 2") > dry_before


def test_4_degree_days_count_from_the_recorded_temperatures(journey: Journey) -> None:
    journey.advance(DAY)

    cycle = journey.call("GET", f"/cycles/{journey.cycle_id}", "farmer")

    assert cycle["accumulated_gdd"] > 0 and cycle["gdd_updated_through"] is not None


def test_5_the_chat_answers_about_the_crop_and_nothing_else(journey: Journey) -> None:
    def ask(question: str) -> Any:
        body = {"plot_id": journey.plot_id, "question": question}
        return journey.call("POST", "/agent/chat", "farmer", json=body)

    about_the_field = ask("How are my zones?")
    off_topic = ask("Who won the football match?")

    journey.notes.append(f"chat in scope: topic {about_the_field['topic']!r}, "
                         f"answer {about_the_field['answer']!r}")  # fmt: skip
    journey.notes.append(f"chat off topic: topic {off_topic['topic']!r}")
    assert about_the_field["status"] == "completed" and about_the_field["answer"]
    assert about_the_field["topic"] in FARM_TOPICS
    if not journey.live:
        assert about_the_field["topic"] == "field" and "Zone 2" in about_the_field["answer"]
    assert off_topic["topic"] == "out_of_scope"
    assert off_topic["answer"].startswith("I can only help with your crop")
    assert "Real Madrid" not in off_topic["answer"]  # the model's text never reaches the farmer


# --- stage 3: from the harvest to the customer's door --------------------------------------


def test_6_the_harvest_becomes_a_lot_with_a_verified_passport(journey: Journey) -> None:
    journey.advance(2 * DAY)
    harvest = {"harvested_on": journey.today().isoformat(), "quantity_kg": 500, "grade": "first"}

    lot = journey.call("POST", f"/cycles/{journey.cycle_id}/harvest", "farmer", json=harvest)
    passport = journey.call("GET", f"/trace/{lot['code']}")

    journey.lot_code = lot["code"]
    assert passport["integrity"]["verified"] is True
    assert [step["step"] for step in passport["journey"]] == ["commissioning"]
    journey.notes.append(f"passport cultivation: {passport.get('cultivation')}")
    assert "latitude" not in passport and passport["producer"]  # public, without the plot


def test_7_the_lot_goes_through_the_bogota_warehouse(journey: Journey) -> None:
    journey.stack.create_account(OPERATOR, "E2E operator", "operator")
    journey.login(OPERATOR, "operator")

    listing = journey.call("POST", f"/lots/{journey.lot_code}/listings", "farmer",
                           json={"farmer_price_per_kg_cop": 3000})  # fmt: skip
    shipment = journey.call("POST", f"/listings/{listing['id']}/dispatch", "farmer")
    received = journey.call("POST", f"/shipments/{shipment['id']}/receive", "operator",
                            json={"received_kg": 498, "temperature_c": 9.5})  # fmt: skip

    journey.listing_id = listing["id"]
    assert listing["warehouse"]["code"] == "BOG-01" and listing["farmer_share_pct"] >= 80
    assert (received["status"], received["stock_kg"]) == ("active", 498.0)
    steps = [s["step"] for s in journey.call("GET", f"/trace/{journey.lot_code}")["journey"]]
    assert steps == ["commissioning", "shipping", "receiving"]


def test_8_the_shopping_assistant_proposes_and_the_customer_buys(journey: Journey) -> None:
    journey.register(CUSTOMER, "customer")
    profile = {"delivery_address": "Calle 80 # 10-20, Bogotá", "consent_profiling": True}
    journey.call("PUT", "/store/profile", "customer", json=profile)

    [product] = journey.call("GET", "/store/products?q=maize")
    answer = journey.call("POST", "/store/assistant", "customer",
                          json={"question": "What should I buy this week?"})  # fmt: skip
    journey.notes.append(f"shopper: topic {answer['topic']!r}, proposal "
                         f"{None if answer['proposal'] is None else answer['proposal']['items']}, "
                         f"answer {answer['answer']!r}")  # fmt: skip
    follow_up = journey.call("POST", "/store/assistant", "customer",
                             json={"question": "What about now?",
                                   "conversation_id": answer["conversation_id"]})  # fmt: skip
    journey.notes.append(f"shopper follow-up: answer {follow_up['answer']!r}")
    assert follow_up["conversation_id"] == answer["conversation_id"]
    assert follow_up["topic"] in STORE_TOPICS and follow_up["answer"]
    if answer["proposal"] is not None:
        journey.call("POST", f"/store/cart-proposals/{answer['proposal']['id']}/accept",
                     "customer")  # fmt: skip
    # One kilogram, whatever the model proposed, so the stock and payout below are exact.
    cart = journey.call("PUT", f"/store/cart/items/{journey.listing_id}", "customer",
                        json={"quantity_kg": 1})  # fmt: skip
    suggestion = journey.call("GET", "/store/cart/suggestion", "customer")
    order = journey.call("POST", "/store/checkout", "customer")

    assert product["id"] == journey.listing_id and product["producer"].endswith("Neiva, Huila")
    assert answer["topic"] in STORE_TOPICS and answer["answer"]
    if not journey.live:
        assert answer["topic"] == "products" and "per kg" in answer["answer"]
        assert answer["proposal"]["items"] == [{"listing_id": journey.listing_id,
                                                "quantity_kg": 1}]  # fmt: skip
    assert [line["listing_id"] for line in cart["lines"]] == [journey.listing_id]
    assert suggestion["recommendation"] is None  # the only product is already in the cart
    assert suggestion["message"].startswith("Your cart looks complete")
    assert order["status"] == "paid" and order["lines"][0]["lot_code"] == journey.lot_code
    off_topic = journey.call("POST", "/store/assistant", "customer",
                             json={"question": "Teach me Python"})  # fmt: skip
    assert (off_topic["topic"], off_topic["proposal"]) == ("out_of_scope", None)

    delivered = journey.call("POST", f"/orders/{order['id']}/deliver", "operator")
    passport = journey.call("GET", f"/trace/{journey.lot_code}")
    [mine] = journey.call("GET", "/listings", "farmer")

    assert delivered["status"] == "delivered"
    assert passport["journey"][-1]["step"] == "retail_selling"
    assert passport["integrity"]["verified"] is True
    assert (mine["sold_kg"], mine["stock_kg"]) == (1.0, 497.0) and mine["payouts_cop"] > 0


def test_9_near_its_best_before_day_the_product_is_marked_down(journey: Journey) -> None:
    for _ in range(2):  # maize keeps 90 days; at 36 days left the first step applies
        journey.advance(28 * DAY, tick=False)

    [deal] = journey.call("GET", "/store/offers/today")
    [mine] = journey.call("GET", "/listings", "farmer")

    assert deal["id"] == journey.listing_id and deal["offer"]["source"] == "clearance"
    assert deal["price"]["farmer_share_pct"] >= 80
    assert mine["clearance"]["discount_pct"] == deal["offer"]["discount_pct"]


def test_10_the_agents_kept_to_the_backends_checks(
    journey: Journey, request: pytest.FixtureRequest
) -> None:
    """Fake: no turn was refused. Live: the model's report card, from the agent trace."""
    trace = journey.call("GET", "/events?kind=agent_tool_call&limit=5000", "farmer")

    if journey.live:
        terminal = request.config.pluginmanager.get_plugin("terminalreporter")
        assert terminal is not None
        lines = ["", "=== Muse report card (e2e-live) ===", *_report_card(trace),
                 "--- the journey ---", *journey.notes]  # fmt: skip
        for line in lines:
            terminal.write_line(line)
        return
    log = journey.stack.muse_log()
    agents = {turn["agent"] for turn in log}
    refused = [turn for turn in log if turn["refusals"]]
    assert agents >= {"agronomist", "monitoring", "imaging", "crop_health", "soil_nutrition",
                      "irrigation", "reporting", "orchestrator", "shopper"}  # fmt: skip
    assert refused == [], refused
    assert all(entry["inputs"]["error"] is None for entry in trace)


def _report_card(trace: list[Any]) -> list[str]:
    """Per farm subagent: turns, refusals (with the first reason) and tokens."""
    lines = []
    for subagent in ("agronomist", "monitoring", "imaging", "crop_health", "soil_nutrition",
                     "irrigation", "reporting", "orchestrator"):  # fmt: skip
        entries = [e["inputs"] for e in trace if e["inputs"]["subagent"] == subagent]
        refusals = [e["error"] for e in entries if e["error"]]
        tokens = sum(e["usage"]["input_tokens"] + e["usage"]["output_tokens"] for e in entries)
        line = (
            f"{subagent:<15} {len(entries):>3} turns  {len(refusals):>2} refused  {tokens:>7} tok"
        )
        lines.append(line + (f"  first refusal: {refusals[0][:120]}" if refusals else ""))
    return lines


def _settle_tasks(journey: Journey, task_ids: list[int]) -> None:
    """Approve what waits for the farmer, then tick until nothing is open; the harvest
    needs no open task. Live, a task the model scheduled far ahead is rejected."""
    for task_id in task_ids:
        if _task(journey, task_id)["status"] == "pending_approval":  # the gate asked
            journey.call("POST", f"/tasks/{task_id}/approve", "farmer")
    for _ in range(6):  # due tasks run on the tick
        if all(_task(journey, t)["status"] not in OPEN for t in task_ids):
            return
        journey.advance(HOUR)
    for task_id in task_ids:
        if _task(journey, task_id)["status"] in OPEN:
            journey.call("POST", f"/tasks/{task_id}/reject", "farmer")


def _do_manual_tasks(journey: Journey, task_ids: list[int]) -> None:
    """The farmer approves the agronomist's tasks and does them by hand (D093)."""
    for task_id in task_ids:
        if _task(journey, task_id)["status"] == "pending_approval":
            journey.call("POST", f"/tasks/{task_id}/approve", "farmer")
        if _task(journey, task_id)["status"] == "scheduled":
            journey.call("POST", f"/tasks/{task_id}/done", "farmer")


def _task(journey: Journey, task_id: int) -> Any:
    [task] = [t for t in journey.call("GET", "/tasks", "farmer") if t["id"] == task_id]
    return task
