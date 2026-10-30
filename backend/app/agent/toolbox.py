"""Builds the tools of one daily cycle or chat turn, bound to its plot, ledger and brief."""

from app.agent.brief import BriefDraft
from app.agent.field import ActionProposer, FarmerOutbox
from app.agent.tools.field_tools import ReadContext, read_tools
from app.agent.tools.irrigation import irrigation_tools
from app.agent.tools.monitoring import monitoring_tools
from app.agent.tools.orchestrator import Consultant, orchestrator_tools
from app.agent.tools.registry import ToolRegistry
from app.agent.tools.reporting import reporting_tools


def cycle_registry(
    read: ReadContext,
    draft: BriefDraft,
    proposer: ActionProposer,
    outbox: FarmerOutbox,
    consultant: Consultant,
) -> ToolRegistry:
    """Every tool of the catalogue. Each subagent sees only its subset (D054)."""
    return ToolRegistry(
        [
            *read_tools(read),
            *monitoring_tools(read, draft),
            *irrigation_tools(read, draft, proposer),
            *reporting_tools(read, outbox),
            *orchestrator_tools(read, draft, consultant),
        ]
    )
