"""Real services around a World, with a replayed model, for the agent pipeline tests."""

from itertools import count

from app.agent.catalog import load_agent_catalog
from app.agent.llm.ports import LLMClient
from app.satellite.config import load_imaging_config
from app.satellite.scenes import ImageryLoader
from app.satellite.segmentation import MockSegmentation, parse_boxes
from app.services.agent_outbox import StoredOutbox
from app.services.agent_proposals import GateProposer
from app.services.agent_session import AgentDeps
from app.services.agent_trace import EventLogTraceSink
from app.services.field_reader import StoredFieldReader
from app.services.imagery_reader import StoredImageryReader
from tests.conftest import CONFIG_DIR, SAM_FIXTURES, SATELLITE_DIR
from tests.integration.services.world import CROPS, MESSAGES, World

CATALOGUE = load_agent_catalog(CONFIG_DIR / "agents")
IMAGING = load_imaging_config(CONFIG_DIR / "imaging.yaml")
# SAM 3.1's recorded answer for the demo image: the three brown patches.
SAM_BOXES = parse_boxes((SAM_FIXTURES / "neiva_brown_patch.txt").read_text(encoding="utf-8"))


def agent_deps(world: World, llm: LLMClient, max_turns: int = 12) -> AgentDeps:
    ids = count(1)
    return AgentDeps(
        llm=llm,
        reader=StoredFieldReader(world.uow, world.forecast, CROPS, world.clock),
        proposer=GateProposer(world.uow, world.proposals, MESSAGES),
        outbox=StoredOutbox(world.uow, world.clock, MESSAGES),
        trace=EventLogTraceSink(world.uow, world.clock),
        imagery=StoredImageryReader(
            world.uow,
            ImageryLoader.from_directory(SATELLITE_DIR),
            MockSegmentation(SAM_BOXES),
            IMAGING,
        ),
        clock=world.clock,
        subagents=CATALOGUE,
        max_turns=max_turns,
        new_id=lambda: f"s{next(ids)}",
    )
