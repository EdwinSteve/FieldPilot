"""Real services around a World, with a replayed model, for the agent pipeline tests."""

from itertools import count

from app.agent.catalog import load_agent_catalog
from app.agent.llm.ports import LLMClient
from app.services.agent_outbox import StoredOutbox
from app.services.agent_proposals import GateProposer
from app.services.agent_session import AgentDeps
from app.services.agent_trace import EventLogTraceSink
from app.services.field_reader import StoredFieldReader
from tests.conftest import CONFIG_DIR
from tests.integration.services.world import CROPS, MESSAGES, World

CATALOGUE = load_agent_catalog(CONFIG_DIR / "agents")


def agent_deps(world: World, llm: LLMClient, max_turns: int = 12) -> AgentDeps:
    ids = count(1)
    return AgentDeps(
        llm=llm,
        reader=StoredFieldReader(world.uow, world.forecast, CROPS, world.clock),
        proposer=GateProposer(world.uow, world.proposals, MESSAGES),
        outbox=StoredOutbox(world.uow, world.clock, MESSAGES),
        trace=EventLogTraceSink(world.uow, world.clock),
        clock=world.clock,
        subagents=CATALOGUE,
        max_turns=max_turns,
        new_id=lambda: f"s{next(ids)}",
    )
