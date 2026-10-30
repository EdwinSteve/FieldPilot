from collections.abc import Callable

import pytest

from app.agent.llm.mock import MockLLMClient
from app.agent.loop import RunStatus
from app.agent.messages import LLMResponse, ToolCall, UserMessage
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.chat import ChatService
from app.services.voice_chat import VoiceChatService
from app.voice.speech import MockSpeechToText, NothingHeardError
from tests.integration.agent.session import agent_deps
from tests.integration.services.world import World
from tests.unit.voice.wavs import make_wav

UowFactory = Callable[[], SqlUnitOfWork]
QUESTION = "¿Necesita agua el maíz de la zona dos?"


def _answer(text: str) -> LLMResponse:
    arguments = f'{{"text_es": "{text}", "cited": []}}'
    return LLMResponse(None, ToolCall("c1", "answer_farmer", arguments))


def test_the_transcript_becomes_the_question(uow: UowFactory) -> None:
    world = World(uow)
    llm = MockLLMClient([_answer("Lo decide el ciclo diario.")])
    speech = MockSpeechToText(QUESTION)
    audio = make_wav()

    answer = VoiceChatService(ChatService(uow, agent_deps(world, llm)), speech).ask(
        world.plot_id, audio
    )

    assert answer.transcript == QUESTION
    assert answer.run.status is RunStatus.COMPLETED
    assert llm.requests[0].messages[0] == UserMessage(QUESTION)
    assert speech.calls == [(audio, "es")]


def test_silence_never_reaches_the_model(uow: UowFactory) -> None:
    world = World(uow)
    llm = MockLLMClient([])

    service = VoiceChatService(ChatService(uow, agent_deps(world, llm)), MockSpeechToText(""))

    with pytest.raises(NothingHeardError):
        service.ask(world.plot_id, make_wav())
    assert llm.requests == []
