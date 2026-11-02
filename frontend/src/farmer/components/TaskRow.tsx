import type { Level } from "../lib/statusLevel";
import type { PlanTask, TaskState } from "../view-models/types";
import { Icon } from "./Icon";
import { CardIcon } from "./IconCircle";
import { LEVEL_TEXT, LEVEL_TILE } from "./levelStyle";

const STATE_LEVELS: Record<TaskState, Level> = {
  done: "good",
  automatic: "good",
  can_undo: "info",
  said_no: "neutral",
  needs_you: "watch",
  planned: "info",
  cancelled: "neutral",
  failed: "bad",
};

interface TaskRowProps {
  task: PlanTask;
  onOpen: (task: PlanTask) => void;
}

export function TaskRow({ task, onOpen }: TaskRowProps) {
  const crossedOut = task.state === "said_no" || task.state === "cancelled";
  const level = STATE_LEVELS[task.state];
  return (
    <button
      type="button"
      onClick={() => onOpen(task)}
      className={`press flex min-h-18 items-center gap-3.5 rounded-button px-3.5 py-3 ${LEVEL_TILE[level]}`}
    >
      <CardIcon colour={LEVEL_TEXT[level]}>
        <Icon name={task.kind === "water" ? "drop" : "document"} strokeWidth={2} />
      </CardIcon>
      <span className="flex flex-1 flex-col gap-0.75 text-left">
        <span className={`text-body font-bold ${crossedOut ? "text-ink-2 line-through" : "text-ink"}`}>
          {task.title}
        </span>
        <span className="text-caption text-ink-2">{task.when}</span>
      </span>
      <span className="rounded-pill bg-surface px-3 py-1.5 text-caption font-extrabold whitespace-nowrap">
        {task.stateLabel}
      </span>
    </button>
  );
}
