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
from tests.unit.agent.field_fakes import (
    NOW,
    FakeImagery,
    FakeOutbox,
    FakeProposer,
    FakeReader,
    NoConsultant,
)

PROMPTS = CONFIG_DIR / "agents"


def test_the_real_catalogue_loads_every_prompt_with_its_hash() -> None:
    catalogue = load_agent_catalog(PROMPTS)

    assert [agent.name for agent in catalogue] == [spec.name for spec in SUBAGENTS]
    for agent in catalogue:
        english = PROMPTS / "en" / f"{agent.name}.md"  # D084: a language's file wins
        raw = (english if english.is_file() else PROMPTS / f"{agent.name}.md").read_bytes()
        assert agent.system_prompt == raw.decode("utf-8")
        assert agent.prompt_sha256 == hashlib.sha256(raw).hexdigest()


def test_only_irrigation_and_the_agronomist_may_write() -> None:
    """D054, D093: pinned on the real catalogue. Both write only through the gate."""
    writers = [agent.name for agent in load_agent_catalog(PROMPTS) if agent.may_write]

    assert writers == ["irrigation", "agronomist"]


def test_the_agronomist_leads_and_the_specialists_only_read() -> None:
    """D093: it consults every specialist; the two new ones close with their own tool."""
    agents = {a.name: a for a in load_agent_catalog(PROMPTS)}
    agronomist = agents["agronomist"]

    consults = {n for n in agronomist.tool_names if n.startswith("consult_")}
    assert consults == {f"consult_{name}" for name in
                        ("monitoring", "imaging", "crop_health", "soil_nutrition", "irrigation",
                         "reporting")}  # fmt: skip
    assert agronomist.closing_tool == "close_day"
    assert "propose_action" not in agronomist.tool_names  # water belongs to irrigation
    assert agents["crop_health"].closing_tool == "submit_health"
    assert agents["soil_nutrition"].closing_tool == "submit_nutrition"
    assert not agents["crop_health"].may_write and not agents["soil_nutrition"].may_write


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
        FakeImagery(),
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
    assert {"propose_task", "cancel_task", "consult_reporting"}.isdisjoint(orchestrator.tool_names)
    assert "consult_soil_nutrition" in orchestrator.tool_names  # read-only specialists (D093)
    assert "propose_action" not in orchestrator.tool_names


def test_imaging_reads_only() -> None:
    imaging = next(a for a in load_agent_catalog(PROMPTS) if a.name == "imaging")

    assert imaging.closing_tool == "submit_imaging" and not imaging.may_write
    assert imaging.tool_names == {"list_zones", "read_imagery", "submit_imaging"}


def test_spanish_keeps_the_original_prompts() -> None:
    """D084: APP_LANGUAGE=es loads the Spanish-output prompts, untouched."""
    for agent in load_agent_catalog(PROMPTS, language="es"):
        assert agent.system_prompt == (PROMPTS / f"{agent.name}.md").read_text(encoding="utf-8")


def test_english_prompts_never_ask_for_spanish() -> None:
    for agent in load_agent_catalog(PROMPTS, language="en"):
        assert "Spanish" not in agent.system_prompt
        assert "decimal comma" not in agent.system_prompt
