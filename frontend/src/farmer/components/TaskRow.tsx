import type { PlanTask, TaskState } from "../view-models/types";
import { Chip, type ChipTone } from "./Chip";
import { Icon } from "./Icon";
import { IconCircle, type CircleTone } from "./IconCircle";

const STATE_CHIPS: Record<TaskState, ChipTone> = {
  done: "good",
  automatic: "good",
  can_undo: "undo",
  said_no: "neutral",
};

function circleTone(task: PlanTask): CircleTone {
  if (task.kind === "report") return "good";
  return task.state === "said_no" ? "neutral" : "undo";
}

interface TaskRowProps {
  task: PlanTask;
  onOpen: (task: PlanTask) => void;
}

export function TaskRow({ task, onOpen }: TaskRowProps) {
  const crossedOut = task.state === "said_no";
  return (
    <button
      type="button"
      onClick={() => onOpen(task)}
      className="flex min-h-18 items-center gap-3.5 rounded-button bg-surface px-3.5 py-3 text-ink"
    >
      <IconCircle tone={circleTone(task)} size="medium">
        <Icon name={task.kind === "water" ? "drop" : "document"} strokeWidth={2} />
      </IconCircle>
      <span className="flex flex-1 flex-col gap-0.75 text-left">
        <span className={`text-body font-bold ${crossedOut ? "text-ink-3 line-through" : ""}`}>
          {task.title}
        </span>
        <span className="text-caption text-ink-3">{task.when}</span>
      </span>
      <Chip tone={STATE_CHIPS[task.state]}>{task.stateLabel}</Chip>
    </button>
  );
}
