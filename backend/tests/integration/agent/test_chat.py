from collections.abc import Callable

from app.agent.llm.mock import MockLLMClient
from app.agent.loop import RunStatus
from app.agent.messages import LLMResponse, ToolCall
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.chat import ChatService
from tests.integration.agent.session import agent_deps
from tests.integration.services.world import World

OFF_TOPIC = "Solo puedo ayudarte con tu cultivo."

UowFactory = Callable[[], SqlUnitOfWork]


def _call(call_id: str, name: str, arguments: str) -> LLMResponse:
    return LLMResponse(None, ToolCall(call_id, name, arguments))


def test_the_chat_answers_with_a_verified_number(uow: UowFactory) -> None:
    world = World(uow)
    llm = MockLLMClient(
        [
            _call("c1", "read_zone", '{"zone_id": 1}'),
            _call(
                "c2",
                "answer_farmer",
                '{"topic": "field", "text_es": "La zona 2 está al 30 %.", "cited": ["reading-1"]}',
            ),
            _call(
                "c3",
                "answer_farmer",
                '{"topic": "field", "text_es": "La zona 2 está al 20 %.", "cited": ["reading-1"]}',
            ),
        ]
    )

    run = ChatService(uow, agent_deps(world, llm), OFF_TOPIC).ask(
        world.plot_id, "¿Cómo está la zona 2?"
    )

    assert run.status is RunStatus.COMPLETED
    assert run.output == {"answer": "La zona 2 está al 20 %.", "topic": "field"}
    assert run.turns == 3  # the wrong number was refused once


def test_the_chat_creates_no_task(uow: UowFactory) -> None:
    """D057: the orchestrator cannot propose."""
    world = World(uow)
    llm = MockLLMClient(
        [
            _call("c1", "propose_action", '{"action_type": "irrigation"}'),
            _call(
                "c2",
                "answer_farmer",
                '{"topic": "field", "text_es": "No puedo regar desde el chat.", "cited": []}',
            ),
        ]
    )

    run = ChatService(uow, agent_deps(world, llm), OFF_TOPIC).ask(world.plot_id, "Riega la zona 2")

    assert run.status is RunStatus.COMPLETED
    with uow() as u:
        assert u.tasks.list() == []
    first_reply = llm.requests[1].messages[-1]
    assert "Unknown tool 'propose_action'" in getattr(first_reply, "output_json", "")


def test_an_off_topic_question_gets_the_fixed_answer(uow: UowFactory) -> None:
    """D088: what the model writes about another subject never reaches the farmer."""
    world = World(uow)
    off = '{"topic": "out_of_scope", "text_es": "La capital de Francia es París."}'
    llm = MockLLMClient([_call("c1", "answer_farmer", off)])

    run = ChatService(uow, agent_deps(world, llm), OFF_TOPIC).ask(
        world.plot_id, "¿Cuál es la capital de Francia?"
    )

    assert run.status is RunStatus.COMPLETED
    assert run.output == {"answer": OFF_TOPIC, "topic": "out_of_scope"}
