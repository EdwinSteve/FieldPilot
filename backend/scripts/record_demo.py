"""Record the two-day demo against the real model (D076).

Run: make record-demo (needs MUSE_API_KEY; uses the network and the key's
quota). It seeds a throwaway farm, plays the D076 script with every model
answer recorded, and only then replaces data/fixtures/llm/demo/<day>.json, so a
failed run never overwrites a good recording.
"""

import json
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.llm.recording import RecordingLLMClient
from app.container import MOCK_CYCLE_DIRS, RECORDED_FILE, Container
from app.domain.enums import ActionType, TaskStatus
from app.main import create_app
from app.services.demo_seed import seed_demo_farm
from app.settings import Settings
from scripts.demo_script import between_days, reject_held, run_day


def main() -> None:
    settings = Settings()
    if settings.mock_llm:
        print("make record-demo needs the real model: run it with MOCK_LLM=0.")
        raise SystemExit(1)
    with tempfile.TemporaryDirectory() as work:
        recordings = Path(work) / "recordings"
        url = f"sqlite:///{Path(work) / 'demo.db'}"
        plot_id = seed_demo_farm(url, settings.app_language).plot_id
        container = create_app(settings.model_copy(update={"database_url": url})).state.container

        day1 = record_day(container, plot_id, recordings)
        held = reject_held(container)
        print(f"Day 1 {day1}: rejected held tasks {held}.")
        rejected = container.queries.tasks(TaskStatus.REJECTED)
        if not any(v.task.action_type is ActionType.IRRIGATION for v in rejected):
            fail("day 1 held no irrigation for approval: the story needs the rain hold.")
        between_days(container)
        day2 = record_day(container, plot_id, recordings)
        tasks = [v.task for v in container.queries.tasks()]
        print(f"Day 2 {day2}: task statuses {sorted(str(t.status) for t in tasks)}.")
        print_tasks(container)
        if not any(t.action_type is ActionType.EXTRA_IRRIGATION
                   and t.status is TaskStatus.SCHEDULED for t in tasks):  # fmt: skip
            fail("day 2 scheduled nothing to revert: the story needs the extra irrigation.")
        if not any(t.action_type is ActionType.IRRIGATION and t.status is TaskStatus.EXECUTED
                   for t in tasks):  # fmt: skip
            fail("day 2 irrigated nothing: the story needs the dry-day irrigation.")

        target = settings.data_dir.joinpath(*MOCK_CYCLE_DIRS[settings.app_language])
        target.mkdir(parents=True, exist_ok=True)
        for recording in sorted(recordings.glob("*.json")):
            shutil.copy2(recording, target / recording.name)
            print(f"Saved {target / recording.name}")
        label = {
            "recorded_on": datetime.now(UTC).date().isoformat(),
            "model": settings.muse_agent_model,
            "daily_cycle": settings.daily_cycle,
        }
        (target / RECORDED_FILE).write_text(json.dumps(label, indent=2) + "\n", encoding="utf-8")
        print(f"Saved {target / RECORDED_FILE}: the replay's label (D094)")


def record_day(container: Container, plot_id: int, recordings: Path) -> str:
    day = container.queries.local_day(plot_id)
    llm = RecordingLLMClient(container.cycle_llm(day), recordings / f"{day.isoformat()}.json")
    result = run_day(container, plot_id, llm).cycle
    runs = ", ".join(f"{r.subagent} {r.status} in {r.turns}" for r in result.runs)
    print(f"Day {day}: {result.status} ({runs}).")
    if str(result.status) != "completed":
        fail(f"the daily cycle of {day} stopped at {result.stopped_at}. Record again.")
    return day.isoformat()


def print_tasks(container: Container) -> None:
    """Every task with what the gate said, so a failed recording can be understood."""
    for view in container.queries.tasks():
        task = view.task
        when = f"{task.scheduled_for:%d %b %H:%M} UTC"
        reason = f"; {view.reason_es}" if view.reason_es else ""
        print(
            f"  task {task.id}: {task.action_type} {task.params} at {when}"
            f" -> {task.status} ({task.effective_level}){reason}"
        )


def fail(message: str) -> None:
    print(f"Not saved: {message}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
