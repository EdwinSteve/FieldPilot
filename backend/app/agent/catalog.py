"""The real subagents: tools and permissions in code, prompts in config (D053, D054, D055)."""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.agent.loop import Subagent
from app.domain.errors import ConfigError

READ_TOOLS = frozenset({"list_zones", "read_zone", "read_forecast", "read_crop_stage"})


@dataclass(frozen=True)
class SubagentSpec:
    name: str
    tool_names: frozenset[str]
    closing_tool: str | None
    may_write: bool = False


SUBAGENTS: tuple[SubagentSpec, ...] = (
    SubagentSpec("monitoring", READ_TOOLS | {"submit_assessment"}, "submit_assessment"),
    SubagentSpec(
        "imaging", frozenset({"list_zones", "read_imagery", "submit_imaging"}), "submit_imaging"
    ),
    SubagentSpec("irrigation", READ_TOOLS | {"propose_action", "finish"}, "finish", may_write=True),
    SubagentSpec("reporting", READ_TOOLS | {"submit_report"}, "submit_report"),
    # The chat is read-only for now (D057).
    SubagentSpec(
        "orchestrator", READ_TOOLS | {"consult_monitoring", "answer_farmer"}, "answer_farmer"
    ),
)

# The customer's shopping assistant (D085): its own catalogue, never the farm's tools.
SHOPPER_TOOLS = frozenset(
    {
        "get_purchase_history",
        "get_recommendations",
        "search_products",
        "get_offers_today",
        "get_passport",
        "propose_cart",
        "answer_customer",
    }
)
SHOPPER = SubagentSpec("shopper", SHOPPER_TOOLS, "answer_customer", may_write=True)


def load_agent_catalog(
    prompts_dir: Path, specs: Sequence[SubagentSpec] = SUBAGENTS, *, language: str = "en"
) -> tuple[Subagent, ...]:
    """Every spec with its prompt file. Refuses a missing prompt or closing tool.

    `<language>/<name>.md` wins over `<name>.md`, so a prompt that sets the
    farmer's language has one file per language and the others are shared (D084).
    """
    problems = [
        f"{spec.name}: no closing tool (D053)" for spec in specs if spec.closing_tool is None
    ]
    files = {spec.name: _prompt_file(prompts_dir, spec.name, language) for spec in specs}
    problems += [
        f"{name}: missing prompt {path} (D055)"
        for name, path in files.items()
        if not path.is_file()
    ]
    if problems:
        raise ConfigError("agent catalogue: " + "; ".join(problems))
    return tuple(_subagent(spec, files[spec.name]) for spec in specs)


def _prompt_file(prompts_dir: Path, name: str, language: str) -> Path:
    localised = prompts_dir / language / f"{name}.md"
    return localised if localised.is_file() else prompts_dir / f"{name}.md"


def _subagent(spec: SubagentSpec, prompt_file: Path) -> Subagent:
    raw = prompt_file.read_bytes()
    return Subagent(
        name=spec.name,
        system_prompt=raw.decode("utf-8"),
        tool_names=spec.tool_names,
        closing_tool=spec.closing_tool,
        may_write=spec.may_write,
        prompt_sha256=hashlib.sha256(raw).hexdigest(),
    )
