"""GateProposer: an agent request goes through ProposalService and the real gate."""

from collections.abc import Callable

from app.agent.field import ActionRequest
from app.persistence.unit_of_work import SqlUnitOfWork
from app.services.agent_proposals import GateProposer
from tests.integration.services.world import DAY1, MESSAGES, World

UowFactory = Callable[[], SqlUnitOfWork]


def _request(world: World, volume_mm: float = 15.0) -> ActionRequest:
    return ActionRequest(
        "irrigation",
        world.plot_id,
        world.zone_id,
        DAY1,
        {"volume_mm": volume_mm},
        "Humedad del 20 %; riego de 15 mm.",
        "agent:irrigation",
    )


def test_an_allowed_irrigation_executes(uow: UowFactory) -> None:
    world = World(uow)

    view = GateProposer(uow, world.proposals, MESSAGES).propose(_request(world))

    assert (view.status, view.outcome, view.effective_level) == (
        "executed",
        "execute",
        "autonomous",
    )
    assert view.reason_es is None and view.already_decided is False
    assert world.task(view.task_id).params == {"volume_mm": 15.0}


def test_a_held_irrigation_carries_the_farmer_reason(uow: UowFactory) -> None:
    world = World(uow)
    world.forecast.mm = 8.0

    view = GateProposer(uow, world.proposals, MESSAGES).propose(_request(world))

    assert (view.status, view.outcome) == ("pending_approval", "await_approval")
    assert view.reason_es == "Pendiente de aprobación por lluvia prevista (8 mm > 5 mm)"


def test_the_same_request_twice_is_one_task(uow: UowFactory) -> None:
    world = World(uow)
    proposer = GateProposer(uow, world.proposals, MESSAGES)

    first = proposer.propose(_request(world))
    second = proposer.propose(_request(world))

    assert second.task_id == first.task_id
    assert second.already_decided is True
