"""Record the two-day demo against the real model (D076).

Run: make record-demo (needs MUSE_API_KEY; uses the network and the key's
quota). It seeds a throwaway farm, plays the D076 script with every model
answer recorded, and only then replaces data/fixtures/llm/demo/<day>.json, so a
failed run never overwrites a good recording.
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.llm.recording import RecordingLLMClient
from app.container import MOCK_CYCLE_DIR, Container
from app.domain.enums import TaskStatus
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
        plot_id = seed_demo_farm(url).plot_id
        container = create_app(settings.model_copy(update={"database_url": url})).state.container

        day1 = record_day(container, plot_id, recordings)
        held = reject_held(container)
        print(f"Day 1 {day1}: rejected held tasks {held}.")
        if not held:
            fail("day 1 held nothing for approval: the story needs the rain hold. Record again.")
        between_days(container)
        day2 = record_day(container, plot_id, recordings)
        statuses = sorted(str(v.task.status) for v in container.queries.tasks())
        print(f"Day 2 {day2}: task statuses {statuses}.")
        print_tasks(container)
        if str(TaskStatus.SCHEDULED) not in statuses:
            fail("day 2 scheduled nothing to revert: the story needs the extra irrigation.")

        target = settings.data_dir.joinpath(*MOCK_CYCLE_DIR)
        target.mkdir(parents=True, exist_ok=True)
        for recording in sorted(recordings.glob("*.json")):
            shutil.copy2(recording, target / recording.name)
            print(f"Saved {target / recording.name}")


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
