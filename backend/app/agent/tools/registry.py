"""Typed tools and the registry that validates every call (§4.8).

A failure the model can fix (unknown tool, bad JSON, invalid arguments, a
refusal by the tool's own check) comes back as `{"error": ...}`. Anything
else is a bug and propagates.
"""

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agent.messages import ToolSpec
from app.domain.errors import ConfigError
from app.domain.models import JsonObject, JsonValue


class ToolRefusedError(Exception):
    """Raised by a handler whose check refuses the call. The message goes to the model."""


@dataclass(frozen=True)
class Tool[In: BaseModel]:
    name: str
    description: str
    input_model: type[In]
    handler: Callable[[In], JsonObject]
    closes_run: bool = False

    def spec(self) -> ToolSpec:
        return ToolSpec(self.name, self.description, self.input_model.model_json_schema())

    def invoke(self, arguments: JsonObject) -> JsonObject:
        """Validate the arguments, then run the handler. Raises `ValidationError`."""
        return self.handler(self.input_model.model_validate(arguments))


@dataclass(frozen=True)
class ToolOutcome:
    """One call through the registry: exactly one of `result` and `error` is set."""

    name: str
    arguments: JsonValue  # the parsed object, or the raw text when it was not valid JSON
    result: JsonObject | None = None
    error: str | None = None
    closes_run: bool = False  # True only for a successful call to a closing tool

    def output_json(self) -> str:
        return json.dumps(self.result if self.error is None else {"error": self.error})


class ToolRegistry:
    """Tools by name. A subagent sees only its `subset`."""

    def __init__(self, tools: Iterable[Tool[Any]] = ()) -> None:
        self._tools: dict[str, Tool[Any]] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool[Any]) -> None:
        if tool.name in self._tools:
            raise ConfigError(f"tool {tool.name!r} is registered twice")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool[Any] | None:
        return self._tools.get(name)

    def names(self) -> frozenset[str]:
        return frozenset(self._tools)

    def subset(self, names: Iterable[str]) -> "ToolRegistry":
        wanted = sorted(set(names))
        missing = [name for name in wanted if name not in self._tools]
        if missing:
            raise ConfigError(f"unknown tools: {', '.join(missing)}")
        return ToolRegistry(self._tools[name] for name in wanted)

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(tool.spec() for tool in self._tools.values())

    def call(self, name: str, arguments_json: str) -> ToolOutcome:
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools))
            return ToolOutcome(
                name, arguments_json, error=f"Unknown tool {name!r}. Available: {available}."
            )
        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError as exc:
            return ToolOutcome(
                name, arguments_json, error=f"Arguments are not valid JSON: {exc.msg}."
            )
        if not isinstance(arguments, dict):
            return ToolOutcome(name, arguments, error="Arguments must be a JSON object.")
        try:
            result = tool.invoke(arguments)
        except ValidationError as exc:
            return ToolOutcome(name, arguments, error=_describe(exc))
        except ToolRefusedError as exc:
            return ToolOutcome(name, arguments, error=str(exc))
        return ToolOutcome(name, arguments, result=result, closes_run=tool.closes_run)


def _describe(exc: ValidationError) -> str:
    problems = [
        f"{'.'.join(str(part) for part in error['loc']) or 'arguments'}: {error['msg']}"
        for error in exc.errors(include_url=False)
    ]
    return "Invalid arguments: " + "; ".join(problems) + "."
