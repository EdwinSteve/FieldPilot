import { Icon } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { RareCard } from "../components/RareCard";
import { ScreenBody } from "../components/ScreenBody";
import { UndoCard } from "../components/UndoCard";
import { UpdateRow } from "../components/UpdateRow";
import { en } from "../i18n/en";
import type { UpdatesView } from "../view-models/types";

interface UpdatesScreenProps {
  view: UpdatesView;
  onUndo: (taskId: number) => void;
  onMarkAllRead: () => void;
}

export function UpdatesScreen({ view, onUndo, onMarkAllRead }: UpdatesScreenProps) {
  return (
    <ScreenBody>
      <div className="flex items-end justify-between gap-2.5 px-0.5">
        <div className="flex flex-col gap-0.5">
          <span className="text-small text-ink-3">{view.dateLine}</span>
          <h1 className="text-title font-extrabold tracking-title">{en.updates.title}</h1>
        </div>
        {view.unreadCount > 0 ? (
          <button
            type="button"
            onClick={onMarkAllRead}
            className="min-h-12 rounded-xl border-0 bg-transparent px-3 text-caption font-extrabold text-primary"
          >
            {en.updates.markAllRead}
          </button>
        ) : null}
      </div>
      {view.undo && !view.undone ? <UndoCard item={view.undo} onUndo={onUndo} /> : null}
      {view.undone ? (
        <section className="flex items-center gap-3.5 rounded-card bg-surface px-4.5 py-4">
          <span className="animate-pop-in">
            <IconCircle tone="good" size="large">
              <Icon name="check" size={28} strokeWidth={2.6} />
            </IconCircle>
          </span>
          <span className="flex-1 text-row font-extrabold">{en.updates.cancelled}</span>
        </section>
      ) : null}
      {view.rare.map((item) => (
        <RareCard key={item.kind} item={item} />
      ))}
      <section className="flex flex-col gap-2">
        {view.items.map((item) => (
          <UpdateRow key={item.id} item={item} />
        ))}
        {view.items.length === 0 ? (
          <p className="rounded-tile bg-surface p-4 text-body text-ink-2">{en.updates.empty}</p>
        ) : null}
      </section>
    </ScreenBody>
  );
}
