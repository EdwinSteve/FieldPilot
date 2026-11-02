import avatar from "../assets/avatar.webp";
import { en } from "../i18n/en";
import type { PlanTask } from "../view-models/types";
import { BigButton, BigLink } from "./BigButton";

interface TaskSheetProps {
  task: PlanTask;
  onClose: () => void;
  onUndo: (taskId: number) => void;
}

/** Details of one planned task, sliding over the Plan screen. */
export function TaskSheet({ task, onClose, onUndo }: TaskSheetProps) {
  const undoTaskId = task.undoTaskId;
  return (
    <div className="absolute inset-0 z-10 flex animate-fade-in flex-col justify-end bg-overlay">
      <button
        type="button"
        aria-label={en.plan.closeDetails}
        onClick={onClose}
        className="flex-1 border-0 bg-transparent"
      />
      <dialog
        open
        aria-label={en.plan.taskDetails}
        className="relative m-0 flex w-full max-w-full animate-sheet-up flex-col gap-3.5 rounded-t-sheet border-0 bg-surface px-5 pt-3.5 pb-7 text-ink"
      >
        <span className="h-1.25 w-12 self-center rounded-full bg-border" />
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
          <BigButton variant="undo" onClick={() => onUndo(undoTaskId)}>
            {en.plan.undo}
          </BigButton>
        )}
      </dialog>
    </div>
  );
}
