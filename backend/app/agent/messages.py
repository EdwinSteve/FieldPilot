"""Messages exchanged with the model, and what the model is told about tools (§4.8)."""

from dataclasses import dataclass, field

from app.domain.models import JsonObject


@dataclass(frozen=True)
class UserMessage:
    """The task, a reminder or a nudge. Sent with the user role."""

    text: str


@dataclass(frozen=True)
class AssistantText:
    """Text the model wrote."""

    text: str


@dataclass(frozen=True)
class ToolCall:
    """One tool call requested by the model. The arguments are raw JSON text."""

    call_id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class ToolResult:
    """The JSON answer to a `ToolCall`: the tool's result or `{"error": ...}`."""

    call_id: str
    output_json: str


Message = UserMessage | AssistantText | ToolCall | ToolResult


@dataclass(frozen=True)
class ToolSpec:
    """What the model sees of a tool: its name, description and JSON schema."""

    name: str
    description: str
    parameters: JsonObject


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class LLMResponse:
    """One model turn. At most one tool call, because parallel calls are off (D043)."""

    text: str | None
    tool_call: ToolCall | None
    usage: TokenUsage = field(default_factory=TokenUsage)
