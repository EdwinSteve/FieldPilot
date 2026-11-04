"""Deterministic doubles of the Muse agents, for the end-to-end journey.

Each double plays one subagent the way the prompt asks: it reads with the
real tools, then closes with values taken from what those tools returned. So
the backend's own checks (citations, prices, scope) run for real against a
model that never guesses. A double knows nothing of the database; it sees
only the conversation, as the model does.

A step is a function of the conversation so far: the tools already called and
their JSON results. It returns the next tool call, or None to stop.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

JsonDict = dict[str, Any]

DRY_SHARE_OF_CAPACITY = 0.7  # below 70 % of field capacity a zone is dry
IRRIGATION_MM = 10.0
OFF_TOPIC_WORDS = ("football", "fútbol", "python", "homework", "capital of", "recipe for a poem")


@dataclass(frozen=True)
class Call:
    name: str
    arguments: JsonDict


@dataclass(frozen=True)
class Conversation:
    """What a double sees: the task, the tools it holds, and every call with its result."""

    question: str
    tools: frozenset[str]
    calls: tuple[tuple[Call, JsonDict], ...]

    def results(self, name: str) -> list[JsonDict]:
        return [result for call, result in self.calls if call.name == name]

    def called(self, name: str) -> bool:
        return any(call.name == name for call, _ in self.calls)

    def refusals(self) -> list[str]:
        return [str(result["error"]) for _, result in self.calls if "error" in result]


Step = Callable[[Conversation], Call | None]


def parse(payload: JsonDict) -> Conversation:
    """The Responses API request body, as the double needs it."""
    question, calls = "", []
    pending: dict[str, Call] = {}
    for item in payload.get("input", []):
        kind = item.get("type")
        if kind == "function_call":
            pending[item["call_id"]] = Call(item["name"], json.loads(item["arguments"]))
        elif kind == "function_call_output":
            call = pending.pop(item["call_id"])
            calls.append((call, json.loads(item["output"])))
        elif item.get("role") == "user" and not question:
            question = str(item.get("content", ""))
    tools = frozenset(tool["name"] for tool in payload.get("tools", []))
    return Conversation(question, tools, tuple(calls))


def step_for(conversation: Conversation) -> Step:
    """The subagent is the one whose closing tool the request holds."""
    for closing, step in _STEPS:
        if closing in conversation.tools:
            return step
    raise ValueError(f"no double for the tools {sorted(conversation.tools)}")


# --- the farm ------------------------------------------------------------------------------


def _read_every_zone(conversation: Conversation) -> Call | None:
    """list_zones, then read_zone for each zone not read yet."""
    if not conversation.called("list_zones"):
        return Call("list_zones", {})
    read = {r["zone_id"] for r in conversation.results("read_zone")}
    for zone in conversation.results("list_zones")[0]["zones"]:
        if zone["zone_id"] not in read:
            return Call("read_zone", {"zone_id": zone["zone_id"]})
    return None


def _is_dry(zone: JsonDict) -> bool:
    moisture, capacity = zone["soil_moisture"], zone["field_capacity"]
    if moisture is None or capacity is None:
        return False
    return float(moisture["value"]) < DRY_SHARE_OF_CAPACITY * float(capacity["value"])


def _moisture_ids(zone: JsonDict) -> list[str]:
    return [z["observation_id"] for z in (zone["soil_moisture"], zone["field_capacity"]) if z]


def monitoring(conversation: Conversation) -> Call | None:
    if (next_read := _read_every_zone(conversation)) is not None:
        return next_read
    if not conversation.called("read_forecast"):
        return Call("read_forecast", {})
    zones = [
        {
            "zone_id": zone["zone_id"],
            "status": "dry" if _is_dry(zone) else "ok",
            "moisture_pct": None if zone["soil_moisture"] is None
            else zone["soil_moisture"]["value"],
            "cited": _moisture_ids(zone),
        }
        for zone in conversation.results("read_zone")
    ]  # fmt: skip
    dry = [z["zone_id"] for z in zones if z["status"] == "dry"]
    summary = "Some zones are dry." if dry else "Every zone is within its range."
    return Call("submit_assessment", {"zones": zones, "summary": summary})


def imaging(conversation: Conversation) -> Call | None:
    if not conversation.called("read_imagery"):
        return Call("read_imagery", {})
    view = conversation.results("read_imagery")[0]
    if view["scene"] is None:
        return Call("submit_imaging", {"zones": []})
    threshold = float(view["scene"]["low_ndvi_threshold"])
    zones = []
    for zone in view["zones"]:
        facts = [zone["ndvi"], zone["low_ndvi"], zone["bare_soil"]]
        ndvi = zone["ndvi"]["value"]
        zones.append({
            "zone_id": zone["zone_id"],
            "ndvi_mean": ndvi,
            "low_ndvi_pct": zone["low_ndvi"]["value"],
            "bare_soil_pct": zone["bare_soil"]["value"],
            "low_vigor": ndvi is not None and float(ndvi) < threshold,
            "cited": [fact["observation_id"] for fact in facts],
        })  # fmt: skip
    return Call("submit_imaging", {"zones": zones})


def irrigation(conversation: Conversation) -> Call | None:
    if (next_read := _read_every_zone(conversation)) is not None:
        return next_read
    proposed = {c.arguments["zone_id"] for c, _ in conversation.calls if c.name == "propose_action"}
    for zone in conversation.results("read_zone"):
        if _is_dry(zone) and zone["zone_id"] not in proposed and not zone["upcoming"]:
            return Call("propose_action", {
                "action_type": "irrigation",
                "zone_id": zone["zone_id"],
                "volume_mm": IRRIGATION_MM,
                "scheduled_for": "now",
                "rationale": f"{zone['name']} is dry, so I propose an irrigation now.",
                "cited": _moisture_ids(zone),
            })  # fmt: skip
    return Call("finish", {"summary": "I proposed irrigation for the dry zones."})


def reporting(conversation: Conversation) -> Call | None:
    if (next_read := _read_every_zone(conversation)) is not None:
        return next_read
    actions = {}
    for zone in conversation.results("read_zone"):
        tasks = [*zone["upcoming"], *([zone["last_irrigation"]] if zone["last_irrigation"] else [])]
        for task in tasks:
            actions[task["task_id"]] = {"task_id": task["task_id"], "status": task["status"]}
    text = "Today's report: the zones were assessed and the irrigation tasks are listed."
    return Call("submit_report", {"text_es": text, "cited": [], "actions": list(actions.values())})


def orchestrator(conversation: Conversation) -> Call | None:
    if _off_topic(conversation.question):
        return Call("answer_farmer", {"topic": "out_of_scope", "text_es": "Real Madrid won."})
    if not conversation.called("list_zones"):
        return Call("list_zones", {})
    names = ", ".join(z["name"] for z in conversation.results("list_zones")[0]["zones"])
    return Call("answer_farmer", {"topic": "field", "text_es": f"Your zones: {names}.",
                                  "cited": []})  # fmt: skip


# --- the store -----------------------------------------------------------------------------


def shopper(conversation: Conversation) -> Call | None:
    if _off_topic(conversation.question):
        return Call("answer_customer", {"topic": "out_of_scope", "text": "Python is a snake."})
    if not conversation.called("get_recommendations"):
        return Call("get_recommendations", {"k": 5})
    products = conversation.results("get_recommendations")[0]["products"]
    if not products:
        return Call("answer_customer", {"topic": "products", "text": "Nothing to suggest today."})
    best = products[0]
    if not conversation.called("propose_cart"):
        return Call("propose_cart", {
            "items": [{"listing_id": best["listing_id"], "quantity_kg": 1}],
            "note": f"One kilogram of {best['crop_name']}.",
        })  # fmt: skip
    price = float(best["price_per_kg_cop"])
    text = f"I suggest {best['crop_name']} at ${price:,.0f} per kg; I proposed one kilogram."
    return Call("answer_customer", {"topic": "products", "text": text})


def _off_topic(question: str) -> bool:
    lowered = question.lower()
    return any(word in lowered for word in OFF_TOPIC_WORDS)


_STEPS: Sequence[tuple[str, Step]] = (
    ("submit_assessment", monitoring),
    ("submit_imaging", imaging),
    ("finish", irrigation),
    ("submit_report", reporting),
    ("answer_farmer", orchestrator),
    ("answer_customer", shopper),
)
