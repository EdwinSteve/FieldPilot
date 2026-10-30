import hashlib
from datetime import date
from pathlib import Path

import pytest

from app.agent.brief import BriefDraft, ObservationLedger
from app.agent.catalog import SUBAGENTS, SubagentSpec, load_agent_catalog
from app.agent.llm.mock import MockLLMClient
from app.agent.loop import AgentLoop
from app.agent.toolbox import cycle_registry
from app.agent.tools.field_tools import ReadContext
from app.domain.errors import ConfigError
from tests.conftest import CONFIG_DIR
from tests.fakes import RecordingTrace
from tests.unit.agent.field_fakes import NOW, FakeProposer, FakeReader

PROMPTS = CONFIG_DIR / "agents"


def test_the_real_catalogue_loads_every_prompt_with_its_hash() -> None:
    catalogue = load_agent_catalog(PROMPTS)

    assert [agent.name for agent in catalogue] == [spec.name for spec in SUBAGENTS]
    for agent in catalogue:
        raw = (PROMPTS / f"{agent.name}.md").read_bytes()
        assert agent.system_prompt == raw.decode("utf-8")
        assert agent.prompt_sha256 == hashlib.sha256(raw).hexdigest()


def test_only_irrigation_may_write() -> None:
    """D054: pinned on the real catalogue."""
    writers = [agent.name for agent in load_agent_catalog(PROMPTS) if agent.may_write]

    assert writers == ["irrigation"]


def test_every_real_subagent_has_a_closing_tool() -> None:
    """D053."""
    assert all(agent.closing_tool for agent in load_agent_catalog(PROMPTS))


def test_only_irrigation_holds_propose_action() -> None:
    holders = [a.name for a in load_agent_catalog(PROMPTS) if "propose_action" in a.tool_names]

    assert holders == ["irrigation"]


def test_the_real_catalogue_passes_loop_validation() -> None:
    registry = cycle_registry(
        ReadContext(1, FakeReader(), ObservationLedger(), lambda: NOW),
        BriefDraft(1, date(2026, 10, 28)),
        FakeProposer(),
    )

    loop = AgentLoop(MockLLMClient([]), registry, RecordingTrace(), load_agent_catalog(PROMPTS), 12)

    assert isinstance(loop, AgentLoop)


def test_a_missing_prompt_stops_startup(tmp_path: Path) -> None:
    (tmp_path / "monitoring.md").write_text("prompt", encoding="utf-8")

    with pytest.raises(ConfigError, match=r"irrigation: missing prompt .*irrigation\.md \(D055\)"):
        load_agent_catalog(tmp_path)


def test_a_subagent_without_closing_tool_stops_startup(tmp_path: Path) -> None:
    (tmp_path / "chat.md").write_text("prompt", encoding="utf-8")
    spec = SubagentSpec("chat", frozenset({"read_zone"}), closing_tool=None)

    with pytest.raises(ConfigError, match=r"chat: no closing tool \(D053\)"):
        load_agent_catalog(tmp_path, [spec])
