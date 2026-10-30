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


def load_agent_catalog(
    prompts_dir: Path, specs: Sequence[SubagentSpec] = SUBAGENTS
) -> tuple[Subagent, ...]:
    """Every spec with its prompt file. Refuses a missing prompt or closing tool."""
    problems = [
        f"{spec.name}: no closing tool (D053)" for spec in specs if spec.closing_tool is None
    ]
    problems += [
        f"{spec.name}: missing prompt {prompts_dir / f'{spec.name}.md'} (D055)"
        for spec in specs
        if not (prompts_dir / f"{spec.name}.md").is_file()
    ]
    if problems:
        raise ConfigError("agent catalogue: " + "; ".join(problems))
    return tuple(_subagent(spec, prompts_dir / f"{spec.name}.md") for spec in specs)


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
