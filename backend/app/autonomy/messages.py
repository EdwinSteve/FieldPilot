"""Farmer-facing message catalog (config/messages/<language>.yaml), keyed by code.

Rules and the gate only produce codes and numbers; this is the single place
that turns them into text, in the language of APP_LANGUAGE (English by
default, Spanish kept, D084).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

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
        "producer_of",  # D083: the public passport
        "producer_unknown",
    }
)
# Agent texts, addressed as "<section>.<key>" (D051, D052).
REQUIRED_UNAVAILABLE = frozenset(
    {"llm_unavailable", "speech_unavailable", "chat_unavailable", "fixture_exhausted"}
)
REQUIRED_AGENT_TEXTS = frozenset(
    {"cycle.failed_turn_limit", "cycle.paused_retry_next_run", "report.escalated_unverified"}
)


class _MessagesFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    language: str
    decimal_separator: Literal[".", ","]
    rules: dict[RuleCode, str]
    inputs: dict[str, str]
    labels: dict[str, str]
    cycle: dict[str, str]
    report: dict[str, str]
    crops: dict[str, str]
    errors: dict[str, str] = {}
    unavailable: dict[str, str]


@dataclass(frozen=True)
class MessageCatalog:
    rules: Mapping[RuleCode, str]
    inputs: Mapping[str, str]
    labels: Mapping[str, str]
    agent_texts: Mapping[str, str]
    language: str = "en"
    decimal_separator: str = "."
    crops: Mapping[str, str] = field(default_factory=dict)
    errors: Mapping[str, str] = field(default_factory=dict)  # by error key; may be partial
    unavailable: Mapping[str, str] = field(default_factory=dict)

    def render(self, violation: RuleViolation) -> str:
        """The violation as the farmer reads it, numbers in the catalogue's format."""
        params = {name: self._display(name, value) for name, value in violation.params.items()}
        return self.rules[violation.code].format_map(params)

    def label(self, name: str, **params: str) -> str:
        return self.labels[name].format_map(params)

    def agent_text(self, key: str) -> str:
        """An agent text by its dotted key, e.g. "report.escalated_unverified"."""
        return self.agent_texts[key]

    def crop_name(self, crop: str) -> str:
        """A crop's name for people; its identifier when the catalogue has none."""
        return self.crops.get(crop, crop)

    def error(self, key: str, params: Mapping[str, object], fallback: str) -> str:
        """An API error in this language; the code's English text when the key is absent."""
        template = self.errors.get(key)
        if template is None:
            return fallback
        return template.format_map({k: self._display(k, v) for k, v in params.items()})

    def number(self, value: float) -> str:
        return format_number(value, self.decimal_separator)

    def _display(self, name: str, value: object) -> str:
        if name == "input" and isinstance(value, str):
            return self.inputs.get(value, value)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return format_number(value, self.decimal_separator)
        return str(value)


def format_number(value: float, decimal_separator: str = ",") -> str:
    """Up to two decimals, no trailing zeros: 20.01 -> '20,01' (es) or '20.01' (en)."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", decimal_separator)


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
    problems += [
        f"no unavailable text {key}"
        for key in sorted(REQUIRED_UNAVAILABLE - set(parsed.unavailable))
    ]
    if problems:
        raise ConfigError(f"{path.name}: " + "; ".join(problems))
    return MessageCatalog(
        rules=parsed.rules,
        inputs=parsed.inputs,
        labels=parsed.labels,
        agent_texts=agent_texts,
        language=parsed.language,
        decimal_separator=parsed.decimal_separator,
        crops=parsed.crops,
        errors=parsed.errors,
        unavailable=parsed.unavailable,
    )
