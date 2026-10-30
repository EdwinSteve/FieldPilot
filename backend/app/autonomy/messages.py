"""Farmer-facing message catalog (config/messages/es.yaml), keyed by RuleCode.

Rules and the gate only produce codes and numbers; this is the single place
that turns them into Spanish text.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from app.domain.errors import ConfigError
from app.domain.violations import RuleCode, RuleViolation

REQUIRED_LABELS = frozenset(
    {
        "already_decided",
        "notify_committed",
        "scheduled_not_executed",
        "execution_failed",
        "execution_not_confirmed",
        "irrigation_interrupted",
    }
)
# Agent texts, addressed as "<section>.<key>" (D051, D052).
REQUIRED_AGENT_TEXTS = frozenset(
    {"cycle.failed_turn_limit", "cycle.paused_retry_next_run", "report.escalated_unverified"}
)


class _MessagesFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rules: dict[RuleCode, str]
    inputs: dict[str, str]
    labels: dict[str, str]
    cycle: dict[str, str]
    report: dict[str, str]


@dataclass(frozen=True)
class MessageCatalog:
    rules: Mapping[RuleCode, str]
    inputs: Mapping[str, str]
    labels: Mapping[str, str]
    agent_texts: Mapping[str, str]

    def render(self, violation: RuleViolation) -> str:
        """The violation as the farmer reads it, numbers in Spanish format."""
        params = {name: self._display(name, value) for name, value in violation.params.items()}
        return self.rules[violation.code].format_map(params)

    def label(self, name: str, **params: str) -> str:
        return self.labels[name].format_map(params)

    def agent_text(self, key: str) -> str:
        """An agent text by its dotted key, e.g. "report.escalated_unverified"."""
        return self.agent_texts[key]

    def _display(self, name: str, value: float | str) -> str:
        if name == "input" and isinstance(value, str):
            return self.inputs.get(value, value)
        if isinstance(value, int | float):
            return format_number(value)
        return value


def format_number(value: float) -> str:
    """Up to two decimals, no trailing zeros, decimal comma: 20.01 -> '20,01', 5.0 -> '5'."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def load_message_catalog(path: Path) -> MessageCatalog:
    """Load the catalog. A RuleCode or required label without text raises ConfigError."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        parsed = _MessagesFile.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise ConfigError(f"{path.name}: {error}") from error
    problems = [f"no message for rule code {code}" for code in RuleCode if code not in parsed.rules]
    problems += [f"no label {name}" for name in sorted(REQUIRED_LABELS - set(parsed.labels))]
    agent_texts = {
        f"{section}.{key}": text
        for section, texts in (("cycle", parsed.cycle), ("report", parsed.report))
        for key, text in texts.items()
    }
    problems += [f"no agent text {key}" for key in sorted(REQUIRED_AGENT_TEXTS - set(agent_texts))]
    if problems:
        raise ConfigError(f"{path.name}: " + "; ".join(problems))
    return MessageCatalog(
        rules=parsed.rules, inputs=parsed.inputs, labels=parsed.labels, agent_texts=agent_texts
    )
