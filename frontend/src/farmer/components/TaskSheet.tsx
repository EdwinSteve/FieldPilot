import avatar from "../assets/avatar.webp";
import { en } from "../i18n/en";
import type { PlanTask } from "../view-models/types";
import { BigButton, BigLink } from "./BigButton";
import { Sheet } from "./Sheet";

interface TaskSheetProps {
  task: PlanTask;
  /** True while the Undo is on its way: the button says so and takes no second tap. */
  undoing?: boolean;
  onClose: () => void;
  onUndo: (taskId: number) => void;
}

/** Details of one planned task, sliding over the Plan screen. */
export function TaskSheet({ task, undoing = false, onClose, onUndo }: TaskSheetProps) {
  const undoTaskId = task.undoTaskId;
  return (
    <Sheet label={en.plan.taskDetails} onClose={onClose}>
      <div className="flex flex-col gap-1">
        <span className="text-head font-extrabold">{task.title}</span>
        <span className="text-small text-ink-3">{task.when}</span>
      </div>
      <div className="flex flex-col gap-2.5 rounded-control bg-ground px-4 py-3.5">
        <div className="flex items-center gap-2.5">
          <img src={avatar} alt="" className="size-6.5 rounded-lg object-cover" />
          <span className="text-small text-ink-2">{en.plan.plannedBy}</span>
          <span className="text-small font-extrabold">{task.source}</span>
        </div>
        <span className="text-body leading-relaxed">{task.why}</span>
      </div>
      {task.decideHref === null ? null : (
        <BigLink variant="needs" href={task.decideHref}>
          {en.plan.answer}
        </BigLink>
      )}
      {undoTaskId === null ? (
        <BigButton variant="outline" onClick={onClose}>
          {en.plan.close}
        </BigButton>
      ) : (
        <BigButton variant="undo" disabled={undoing} onClick={() => onUndo(undoTaskId)}>
          {undoing ? en.plan.undoing : en.plan.undo}
        </BigButton>
      )}
    </Sheet>
  );
}
