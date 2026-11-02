import { en } from "../i18n/en";
import type { UndoItem } from "../view-models/types";
import { BigButton } from "./BigButton";
import { Icon } from "./Icon";
import { IconCircle } from "./IconCircle";

interface UndoCardProps {
  item: UndoItem;
  onUndo: (taskId: number) => void;
}

export function UndoCard({ item, onUndo }: UndoCardProps) {
  return (
    <section className="flex flex-col gap-3.5 rounded-card border-[2.5px] border-undo bg-surface p-4.5">
      <div className="flex items-center gap-3.5">
        <IconCircle tone="undo" size="large">
          <Icon name="drop" size={28} strokeWidth={2} />
        </IconCircle>
        <div className="flex flex-1 flex-col gap-0.5">
          <span className="text-key font-extrabold">{item.title}</span>
          <span className="text-small text-ink-2">{item.detail}</span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Icon name="hourglass" size={28} strokeWidth={2} className="text-undo-icon" />
        <div className="h-3.5 flex-1 overflow-hidden rounded-full bg-undo-tint">
          <div
            className="h-full rounded-full bg-undo"
            style={{ width: `${item.remaining * 100}%` }}
          />
        </div>
        <span className="text-body font-extrabold text-undo-text">{item.timeLeft}</span>
      </div>
      <BigButton variant="undo" onClick={() => onUndo(item.taskId)}>
        <Icon name="undo" strokeWidth={2.6} />
        {en.updates.undo}
      </BigButton>
    </section>
  );
}
