"""The port every model client implements, and the two ways a call can fail."""

from collections.abc import Sequence
from typing import Protocol

from app.agent.messages import LLMResponse, Message, ToolSpec


class LLMUnavailableError(Exception):
    """The model service could not answer. The only failure that pauses a run (D048)."""


class FixtureExhaustedError(Exception):
    """The mock has no recorded response for this call (D049).

    Deliberately not an `LLMUnavailableError`: a broken fixture must fail the
    test, not pass as a paused run.
    """


class LLMClient(Protocol):
    def complete(
        self, instructions: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> LLMResponse: ...
