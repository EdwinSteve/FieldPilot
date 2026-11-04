import { useEffect, useRef, useState, type Ref } from "react";
import type { StageState } from "../../lib/stages";
import { BackLink } from "../components/BackHeader";
import { BigButton } from "../components/BigButton";
import { DoneBanner } from "../components/DoneBanner";
import { HarvestSheet, type HarvestNote } from "../components/HarvestSheet";
import { Icon, PlantIcon } from "../components/Icon";
import { TaskRow } from "../components/TaskRow";
import { TaskSheet } from "../components/TaskSheet";
import { en } from "../i18n/en";
import type { PlanDay, PlanTask, PlanView } from "../view-models/types";

const STEP_COLOURS: Record<StageState, string> = {
  done: "bg-primary",
  current: "bg-leaf",
  todo: "bg-divider",
};

function CropCard({ view }: { view: PlanView }) {
  return (
    <section className="flex flex-col gap-2 rounded-control bg-surface px-3.5 py-3">
      <div className="flex items-baseline justify-between">
        <span className="text-body font-extrabold">{view.crop}</span>
        <span className="text-caption font-bold text-ink-3">{view.dayCount}</span>
      </div>
      {view.stage ? (
        <>
          <div className="grid grid-cols-6 gap-1">
            {view.stage.steps.map((step, index) => (
              <span key={index} className={`h-2 rounded-full ${STEP_COLOURS[step]}`} />
            ))}
          </div>
          <div className="flex items-center justify-between gap-2 text-caption font-bold">
            <span className="inline-flex items-center gap-1.5 text-primary-hover">
              <PlantIcon size={20} />
              {view.stage.now}
            </span>
            {view.stage.next ? <span className="text-ink-3">{view.stage.next}</span> : null}
          </div>
        </>
      ) : null}
    </section>
  );
}

interface DaySectionProps {
  day: PlanDay;
  onOpen: (task: PlanTask) => void;
  ref?: Ref<HTMLElement>;
}

function DaySection({ day, onOpen, ref }: DaySectionProps) {
  return (
    <section ref={ref} className="flex scroll-mt-1 flex-col gap-2">
      <div className="flex items-center gap-2.5 px-0.5">
        <span
          className={`text-body font-extrabold ${
            day.today ? "rounded-pill bg-primary px-3 py-1 text-surface" : "text-ink"
          }`}
        >
          {day.label}
        </span>
        {day.rain ? (
          <span className="inline-flex items-center gap-1.5 rounded-pill bg-undo-tint px-2.5 py-1 text-caption font-bold text-undo-text">
            <Icon name="cloud" size={16} />
            {day.rain}
          </span>
        ) : null}
      </div>
      {day.tasks.map((task) => (
        <TaskRow key={task.id} task={task} onOpen={onOpen} />
      ))}
      {day.tasks.length === 0 ? (
        <span className="px-1 py-0.5 text-small text-ink-3">{en.plan.nothingPlanned}</span>
      ) : null}
    </section>
  );
}

interface PlanScreenProps {
  view: PlanView;
  onUndo: (taskId: number) => Promise<boolean>;
  /** The crop is harvested: the farm goes back to choosing what to plant. */
  onHarvested: (note: HarvestNote) => void;
}

export function PlanScreen({ view, onUndo, onHarvested }: PlanScreenProps) {
  const [selected, setSelected] = useState<PlanTask | null>(null);
  const [harvesting, setHarvesting] = useState(false);
  const today = useRef<HTMLElement>(null);

  // The plan opens on today, however long the history above it grows.
  useEffect(() => {
    today.current?.scrollIntoView({ block: "start" });
  }, []);

  const [undoing, setUndoing] = useState(false);
  /** What the last Undo did, said at the top until the farmer closes it or opens another task. */
  const [undone, setUndone] = useState<string | null>(null);
  const undo = (taskId: number) => {
    const title = selected?.title ?? "";
    setUndoing(true);
    void onUndo(taskId).then((done) => {
      setUndoing(false);
      if (!done) return; // The failure is already said at the top of the app.
      setSelected(null);
      setUndone(en.plan.undone(title));
    });
  };
  const openTask = (task: PlanTask) => {
    setUndone(null);
    setSelected(task);
  };
  return (
    <>
      <header className="flex flex-col gap-3 px-4.5 pt-5 pb-2">
        <div className="flex items-center gap-3">
          <BackLink />
          <h1 className="text-title-md font-extrabold tracking-title">{en.plan.title}</h1>
        </div>
        {undone === null ? null : <DoneBanner key={undone} text={undone} onClose={() => setUndone(null)} />}
        <CropCard view={view} />
        {view.promise === null ? null : (
          <p className="flex items-start gap-2 px-1 text-small leading-snug text-ink-2">
            <Icon name="shield" size={18} className="mt-0.5 shrink-0" />
            {view.promise}
          </p>
        )}
        {view.harvest === null ? null : (
          <BigButton variant="outline" size="compact" onClick={() => setHarvesting(true)}>
            <PlantIcon size={24} />
            {en.harvest.open}
          </BigButton>
        )}
      </header>
      <main className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pt-1 pb-5">
        {view.days.map((day) => (
          <DaySection
            key={day.label}
            day={day}
            onOpen={openTask}
            ref={day.today ? today : undefined}
          />
        ))}
      </main>
      {selected ? (
        <TaskSheet task={selected} undoing={undoing} onClose={() => setSelected(null)} onUndo={undo} />
      ) : null}
      {harvesting && view.harvest !== null ? (
        <HarvestSheet info={view.harvest} onClose={() => setHarvesting(false)} onSaved={onHarvested} />
      ) : null}
    </>
  );
}
