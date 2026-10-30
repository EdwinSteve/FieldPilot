"""Muse models through the official OpenAI SDK (D043).

The only module that imports `openai`. Every SDK error becomes
`LLMUnavailableError`, carrying the error class and HTTP status only, never
the request, the response body or the key.
"""

from collections.abc import Sequence

import openai
from openai.types.responses import (
    EasyInputMessageParam,
    FunctionToolParam,
    Response,
    ResponseFunctionToolCallParam,
    ResponseInputItemParam,
)
from openai.types.responses.response_input_param import FunctionCallOutput

from app.agent.llm.ports import LLMUnavailableError
from app.agent.messages import (
    AssistantText,
    LLMResponse,
    Message,
    TokenUsage,
    ToolCall,
    ToolResult,
    ToolSpec,
    UserMessage,
)
from app.settings import Settings


class MuseClient:
    """Implements `LLMClient` with `responses.create`, `store=False`, one tool per turn."""

    def __init__(self, client: openai.OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> "MuseClient":
        if settings.muse_api_key is None or not settings.muse_agent_model:
            raise ValueError("MuseClient needs MUSE_API_KEY and MUSE_AGENT_MODEL")
        client = openai.OpenAI(
            api_key=settings.muse_api_key.get_secret_value(),
            base_url=settings.muse_api_base_url,
            timeout=settings.muse_timeout_seconds,
        )
        return cls(client, settings.muse_agent_model)

    def complete(
        self, instructions: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> LLMResponse:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=instructions,
                input=[to_input_item(message) for message in messages],
                tools=[to_tool_param(spec) for spec in tools],
                parallel_tool_calls=False,
                store=False,
            )
        except openai.APIError as exc:
            raise LLMUnavailableError(describe_error(exc)) from None
        return from_response(response)

    def available_models(self) -> frozenset[str]:
        """Model ids this key can use (`GET /v1/models`)."""
        try:
            return frozenset(model.id for model in self._client.models.list())
        except openai.APIError as exc:
            raise LLMUnavailableError(describe_error(exc)) from None


def to_input_item(message: Message) -> ResponseInputItemParam:
    match message:
        case UserMessage(text):
            return EasyInputMessageParam(role="user", content=text)
        case AssistantText(text):
            return EasyInputMessageParam(role="assistant", content=text)
        case ToolCall(call_id, name, arguments_json):
            return ResponseFunctionToolCallParam(
                type="function_call", call_id=call_id, name=name, arguments=arguments_json
            )
        case ToolResult(call_id, output_json):
            return FunctionCallOutput(
                type="function_call_output", call_id=call_id, output=output_json
            )


def to_tool_param(spec: ToolSpec) -> FunctionToolParam:
    return FunctionToolParam(
        type="function",
        name=spec.name,
        description=spec.description,
        parameters=dict(spec.parameters),
        strict=False,
    )


def from_response(response: Response) -> LLMResponse:
    """Text and the first function call. Parallel calls are off, so there is at most one."""
    calls = [item for item in response.output if item.type == "function_call"]
    call = ToolCall(calls[0].call_id, calls[0].name, calls[0].arguments) if calls else None
    usage = response.usage
    return LLMResponse(
        response.output_text or None,
        call,
        TokenUsage(usage.input_tokens, usage.output_tokens) if usage else TokenUsage(),
    )


def describe_error(exc: openai.APIError) -> str:
    status = getattr(exc, "status_code", None)
    return type(exc).__name__ if status is None else f"{type(exc).__name__} (HTTP {status})"
