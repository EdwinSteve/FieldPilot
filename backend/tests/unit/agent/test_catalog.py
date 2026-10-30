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
from tests.unit.agent.field_fakes import NOW, FakeOutbox, FakeProposer, FakeReader, NoConsultant

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
        FakeOutbox(),
        NoConsultant(),
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


def test_the_catalogue_includes_reporting() -> None:
    reporting = next(a for a in load_agent_catalog(PROMPTS) if a.name == "reporting")

    assert reporting.closing_tool == "submit_report" and not reporting.may_write


def test_the_orchestrator_is_read_only() -> None:
    """D057."""
    orchestrator = next(a for a in load_agent_catalog(PROMPTS) if a.name == "orchestrator")

    assert orchestrator.closing_tool == "answer_farmer"
    assert not orchestrator.may_write
    assert "consult_irrigation" not in orchestrator.tool_names
    assert "propose_action" not in orchestrator.tool_names
