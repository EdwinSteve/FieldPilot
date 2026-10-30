"""Builds the tools of one daily cycle or chat turn, bound to its plot, ledger and brief."""

from app.agent.brief import BriefDraft
from app.agent.field import ActionProposer
from app.agent.tools.field_tools import ReadContext, read_tools
from app.agent.tools.irrigation import irrigation_tools
from app.agent.tools.monitoring import monitoring_tools
from app.agent.tools.registry import ToolRegistry


def cycle_registry(read: ReadContext, draft: BriefDraft, proposer: ActionProposer) -> ToolRegistry:
    """Every tool of the catalogue. Each subagent sees only its subset (D054)."""
    return ToolRegistry(
        [
            *read_tools(read),
            *monitoring_tools(read, draft),
            *irrigation_tools(read, draft, proposer),
        ]
    )
