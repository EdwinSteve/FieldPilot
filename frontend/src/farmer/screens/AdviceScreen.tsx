import { useState } from "react";
import { api } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { lifecycle, type CropOutlook, type FarmPlot, type Lot, type PlantingPlan } from "../api/lifecycle";
import { BigButton } from "../components/BigButton";
import { CropCard } from "../components/CropCard";
import { SettingsLink } from "../components/SettingsLink";
import type { HarvestNote } from "../components/HarvestSheet";
import { Icon } from "../components/Icon";
import { Sheet } from "../components/Sheet";
import { SowingStrips } from "../components/SowingStrips";
import { StateView } from "../components/StateView";
import { readDraft } from "../hooks/setupDraftStore";
import { useAdvice } from "../hooks/useAdvice";
import { useLots } from "../hooks/useLots";
import { en } from "../i18n/en";
import { formatCalendarDate } from "../lib/farmTime";
import { orderForGoals, RECOMMENDED } from "../lib/goals";
import { cropLabel, farmLabel } from "../lib/names";
import { nothingGrowsWell, weekOf } from "../lib/plantingPlan";
import { earliestSowing, plotToday, sowingDateProblem } from "../lib/sowingDate";
import { kgText } from "../lib/harvest";
import { startFailure, type StartFailure } from "../lib/startFailure";

/** The planner's "no network" model id (D079). */
const BASELINE_MODEL = "b0-climatology";

/** The phone's own clock, read only when the farmer taps. */
function phoneNow(): string {
  return new Date().toISOString();
}

const loadClock = () => api.clock();

async function firstCheck(plotId: number): Promise<void> {
  try {
    if ((await api.zones(plotId)).length > 0) await api.dailyCycle(plotId);
  } catch {
    // The morning check runs it anyway; nothing here for the farmer to do.
  }
}

interface PlantSheetProps {
  plot: FarmPlot;
  plan: PlantingPlan;
  crop: CropOutlook;
  today: string;
  onClose: () => void;
  onStarted: () => void;
}

/** "I've already planted it": the day, then the backend's own-risk check, then stage 2. */
function PlantSheet({ plot, plan, crop, today, onClose, onStarted }: PlantSheetProps) {
  const [date, setDate] = useState(today);
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<Exclude<StartFailure, "own_risk"> | null>(null);
  const [ownRisk, setOwnRisk] = useState(false);
  const problem = sowingDateProblem(date, today);
  const name = cropLabel(crop.crop);
  const top = (weekOf(plan, date)?.outlooks ?? [])
    .slice(0, RECOMMENDED)
    .map((outlook) => cropLabel(outlook.crop))
    .join(", ");

  const start = async (acceptOwnRisk: boolean) => {
    setTried(true);
    setFailure(null);
    if (problem !== null) return;
    setBusy(true);
    try {
      const cycle = await lifecycle.startCycle(plot.id, {
        crop: crop.crop,
        sowing_date: date,
        accept_own_risk: acceptOwnRisk,
      });
      // Stage 2 takes over now, not tomorrow morning, but only on a farm with sensors:
      // without a zone the check has nothing to read and stops with a failure notice.
      if (cycle.automated) void firstCheck(plot.id);
      onStarted();
    } catch (caught) {
      const reason = startFailure(caught);
      if (reason === "own_risk") setOwnRisk(true);
      else setFailure(reason);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet label={en.advice.plantedTitle(name)} onClose={onClose}>
      {ownRisk ? (
        <>
          <h2 className="text-head font-extrabold tracking-key">{en.advice.ownRiskTitle}</h2>
          <p className="text-body leading-snug">{en.advice.ownRisk(name, top, crop.automatable)}</p>
          <BigButton variant="primary" disabled={busy} onClick={() => void start(true)}>
            {busy ? en.advice.starting : en.advice.ownRiskConfirm}
          </BigButton>
        </>
      ) : (
        <>
          <h2 className="text-head font-extrabold tracking-key">{en.advice.plantedTitle(name)}</h2>
          <label className="flex flex-col gap-2">
            <span className="px-0.5 text-body font-bold text-ink-2">{en.advice.sowingDate}</span>
            <input
              type="date"
              value={date}
              min={earliestSowing(today)}
              max={today}
              aria-invalid={tried && problem !== null}
              onChange={(event) => setDate(event.target.value)}
              className="min-h-16 rounded-control border-2 border-border bg-surface px-4 text-row text-ink"
            />
          </label>
          {tried && problem !== null ? (
            <p className="flex items-center gap-2 px-0.5 text-small font-bold text-bad-text">
              <Icon name="warning" size={18} strokeWidth={2.4} className="shrink-0" />
              {en.advice.sowingProblems[problem]}
            </p>
          ) : null}
          <p className="text-body leading-snug text-ink-2">
            {crop.automatable ? en.advice.startAutomatic : en.advice.startManual}
          </p>
          <BigButton variant="primary" disabled={busy} onClick={() => void start(false)}>
            {busy ? en.advice.starting : en.advice.confirm}
          </BigButton>
        </>
      )}
      {failure === null ? null : (
        <p role="alert" className="rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text">
          {en.advice.startFailures[failure]}
        </p>
      )}
      <BigButton variant="outline" size="compact" onClick={onClose}>
        {en.advice.cancel}
      </BigButton>
    </Sheet>
  );
}

function WeekPicker({
  plan,
  chosen,
  onChoose,
}: {
  plan: PlantingPlan;
  chosen: number;
  onChoose: (index: number) => void;
}) {
  return (
    <fieldset className="-mx-4.5 flex min-w-0 shrink-0 gap-2 overflow-x-auto border-0 px-4.5 pb-1">
      <legend className="sr-only">{en.advice.sowingWeek}</legend>
      {plan.weeks.map((week, index) => (
        <button
          key={week.sowing_date}
          type="button"
          aria-pressed={index === chosen}
          onClick={() => onChoose(index)}
          className={`press min-h-12 shrink-0 rounded-pill border-2 px-4 text-small font-bold ${
            index === chosen ? "border-primary bg-primary text-surface" : "border-border bg-surface text-ink"
          }`}
        >
          {index === 0 ? en.today.thisWeek : en.advice.weekOf(formatCalendarDate(week.sowing_date))}
        </button>
      ))}
    </fieldset>
  );
}

interface Planting {
  crop: CropOutlook;
  today: string;
}

function SavedNote({ note }: { note: HarvestNote }) {
  return (
    <output className="flex shrink-0 gap-3 rounded-card bg-tint px-4.5 py-4 text-primary-hover">
      <Icon name="check" size={24} strokeWidth={2.8} className="mt-0.5 shrink-0" />
      <span className="flex flex-col gap-0.5">
        <span className="text-lead font-extrabold">{en.harvest.saved(kgText(note.kg), note.crop)}</span>
        <span className="text-body">{en.harvest.savedNext}</span>
      </span>
    </output>
  );
}

/** The farm's harvests so far, newest first; nothing before the first. */
function PastHarvests({ lots }: { lots: readonly Lot[] }) {
  if (lots.length === 0) return null;
  return (
    <section className="flex shrink-0 flex-col gap-2.5 rounded-card bg-surface p-4.5">
      <h2 className="text-lead font-bold">{en.harvest.pastTitle}</h2>
      <ul className="flex flex-col gap-2">
        {lots.toSorted((a, b) => b.harvested_on.localeCompare(a.harvested_on)).map((lot) => (
          <li key={lot.code} className="flex flex-col">
            <span className="text-body font-bold">{cropLabel(lot.crop)}</span>
            <span className="text-small text-ink-2">
              {en.harvest.pastRow(
                formatCalendarDate(lot.harvested_on),
                kgText(lot.quantity_kg),
                en.harvest.grades[lot.grade],
              )}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

interface AdviceProps {
  plot: FarmPlot;
  plan: PlantingPlan;
  harvested: HarvestNote | null;
  onPlanted: () => void;
}

function Advice({ plot, plan, harvested, onPlanted }: AdviceProps) {
  const [draft] = useState(readDraft);
  const [weekIndex, setWeekIndex] = useState(0);
  const [planting, setPlanting] = useState<Planting | null>(null);
  const clock = useResource(loadClock, 0);
  const lots = useLots(plot.id);
  // The backend's clock says what today is; the phone's stands in if it has not answered.
  const plant = (crop: CropOutlook) =>
    setPlanting({
      crop,
      today: plotToday(clock.data?.now ?? phoneNow(), plot.utc_offset_hours),
    });
  const week = plan.weeks[weekIndex] ?? plan.weeks[0];
  if (week === undefined) return null;
  const ordered = orderForGoals(week.outlooks, draft.goals);
  const recommended = ordered.slice(0, RECOMMENDED);
  const others = ordered.slice(RECOMMENDED);
  const firstGoal = draft.goals[0] ?? null;
  const poor = nothingGrowsWell(week.outlooks);

  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4.5 pt-7 pb-6">
      <header className="flex items-start justify-between gap-3 px-0.5">
        <div className="flex flex-col gap-1">
          <h1 className="text-title font-extrabold tracking-title">{en.advice.title}</h1>
          <span className="text-lead leading-snug text-ink-2">{en.advice.lead(farmLabel(plot.name))}</span>
        </div>
        <SettingsLink />
      </header>
      {harvested === null ? null : <SavedNote note={harvested} />}
      <WeekPicker plan={plan} chosen={weekIndex} onChoose={setWeekIndex} />
      {poor ? (
        <div role="note" className="flex gap-3 rounded-card bg-bad-tint px-4.5 py-4 text-bad-text">
          <Icon name="warning" size={24} strokeWidth={2.4} className="mt-0.5 shrink-0" />
          <div className="flex flex-col gap-1">
            <h2 className="text-lead font-extrabold">{en.advice.poorTitle}</h2>
            <p className="text-body leading-snug">{en.advice.poorDetail}</p>
          </div>
        </div>
      ) : null}
      <h2 className="px-0.5 pt-1 text-lead font-bold">
        {poor ? en.advice.leastPoor : en.advice.recommended}
      </h2>
      {recommended.map((outlook, index) => (
        <CropCard
          key={outlook.crop}
          outlook={outlook}
          recommended={!poor}
          bestFor={index === 0 && !poor ? firstGoal : null}
          grown={draft.crops.includes(outlook.crop)}
          onPlanted={() => plant(outlook)}
        />
      ))}
      <SowingStrips plan={plan} grown={draft.crops} />
      {others.length === 0 ? null : (
        <>
          <h2 className="px-0.5 pt-1 text-lead font-bold">{en.advice.otherCrops}</h2>
          {others.map((outlook) => (
            <CropCard
              key={outlook.crop}
              outlook={outlook}
              recommended={false}
              bestFor={null}
              grown={draft.crops.includes(outlook.crop)}
              onPlanted={() => plant(outlook)}
            />
          ))}
        </>
      )}
      <PastHarvests lots={lots} />
      <p className="flex items-start gap-2 px-1 text-caption leading-snug text-ink-3">
        <Icon name="info" size={18} className="mt-0.5 shrink-0" />
        {plan.model === BASELINE_MODEL
          ? en.advice.baseline
          : en.advice.modelNote(formatCalendarDate(week.weather_until))}
      </p>
      {planting === null ? null : (
        <PlantSheet
          plot={plot}
          plan={plan}
          crop={planting.crop}
          today={planting.today}
          onClose={() => setPlanting(null)}
          onStarted={onPlanted}
        />
      )}
    </main>
  );
}

interface AdviceScreenProps {
  plot: FarmPlot;
  /** The harvest just saved, said once at the top. */
  harvested: HarvestNote | null;
  /** A crop was started: read the farmer's progress again, which opens the farm. */
  onPlanted: () => void;
}

/** What to sow on the farmer's own plot, from the planner (D079, D081), and the sowing confirmation (D083). */
export function AdviceScreen({ plot, harvested, onPlanted }: AdviceScreenProps) {
  const advice = useAdvice(plot.id);
  switch (advice.status) {
    case "loading":
      return <StateView icon="hourglass" title={en.advice.loadingPlan} />;
    case "preparing":
      return (
        <StateView
          icon="satellite"
          title={en.advice.preparingTitle}
          detail={`${en.advice.preparingDetail} ${en.advice.preparingAgain}`}
        />
      );
    case "site_failed":
      return (
        <StateView icon="warning" title={en.advice.failedTitle} detail={en.advice.failedDetail}>
          <div className="flex w-full max-w-80 flex-col pt-2">
            <BigButton variant="primary" disabled={advice.retrying} onClick={advice.retry}>
              {advice.retrying ? en.state.retrying : en.advice.retry}
            </BigButton>
          </div>
        </StateView>
      );
    case "plan_failed":
      return (
        <StateView icon="warning" title={en.advice.planFailed}>
          <div className="flex w-full max-w-80 flex-col pt-2">
            <BigButton variant="primary" onClick={advice.retry}>
              {en.advice.retry}
            </BigButton>
          </div>
        </StateView>
      );
    case "ready":
      return <Advice plot={plot} plan={advice.plan} harvested={harvested} onPlanted={onPlanted} />;
  }
}
