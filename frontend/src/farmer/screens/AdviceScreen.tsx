import { useEffect, useState } from "react";
import { api } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import {
  lifecycle,
  type CropOutlook,
  type FarmPlot,
  type Lot,
  type PlantingPlan,
  type StartedCycle,
} from "../api/lifecycle";
import { BackLink } from "../components/BackHeader";
import { BigButton } from "../components/BigButton";
import { CropArt } from "../components/CropArt";
import { daysSinceSowing } from "../../lib/stages";
import { CropCard } from "../components/CropCard";
import { SalesCard } from "../components/SalesCard";
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
import { kgText, latestLotOf } from "../lib/harvest";
import { SITE_STEPS, siteStep } from "../lib/siteSteps";
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
  onStarted: (cycle: StartedCycle) => void;
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
      onStarted(cycle);
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
    <fieldset className="-mx-4.5 flex min-w-0 shrink-0 gap-2 overflow-x-auto border-0 px-4.5 pb-3">
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
  /** The farm's data just finished building while the farmer waited. */
  justReady: boolean;
  onPlanted: (cycle: StartedCycle) => void;
  growing: Growing | null;
}

/** The moment the wait ends, so the farmer sees it is done and what comes next. */
function ReadyNote() {
  return (
    <output className="flex animate-card-in gap-3 rounded-card bg-tint px-4.5 py-4 text-primary-hover">
      <Icon name="check" size={24} strokeWidth={2.8} className="mt-0.5 shrink-0" />
      <div className="flex flex-col gap-0.5">
        <p className="text-lead font-extrabold">{en.site.readyTitle}</p>
        <p className="text-body">{en.site.readyDetail}</p>
      </div>
    </output>
  );
}

/** The crop on the farm now, at the top of What to plant next. */
function GrowingNow({ growing, day }: { growing: Growing; day: number }) {
  return (
    <section className="flex shrink-0 items-center gap-3.5 rounded-card bg-primary px-4.5 py-4 text-surface">
      <span className="flex size-14 shrink-0 items-center justify-center rounded-full bg-surface">
        <CropArt crop={growing.crop} size={40} />
      </span>
      <span className="flex flex-col gap-0.5">
        <span className="text-caption font-extrabold tracking-wide uppercase">{en.advice.growingNow}</span>
        <span className="text-row font-extrabold">
          {en.advice.growingSince(cropLabel(growing.crop), formatCalendarDate(growing.sowingDate), day)}
        </span>
      </span>
    </section>
  );
}

function Advice({ plot, plan, harvested, justReady, onPlanted, growing }: AdviceProps) {
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
      {growing === null ? (
        <header className="flex items-start justify-between gap-3 px-0.5">
          <div className="flex flex-col gap-1">
            <h1 className="text-title font-extrabold tracking-title">{en.advice.title}</h1>
            <span className="text-lead leading-snug text-ink-2">{en.advice.lead(farmLabel(plot.name))}</span>
          </div>
          <SettingsLink />
        </header>
      ) : (
        <header className="flex items-start gap-3 px-0.5">
          <BackLink />
          <div className="flex flex-col gap-1">
            <h1 className="text-title font-extrabold tracking-title">{en.advice.nextTitle}</h1>
            <span className="text-lead leading-snug text-ink-2">{en.advice.nextLead}</span>
          </div>
        </header>
      )}
      {growing === null ? null : (
        <GrowingNow
          growing={growing}
          // The backend's day, as the rest of the farm counts it; the phone's until it answers.
          day={daysSinceSowing(growing.sowingDate, clock.data?.now ?? phoneNow(), plot.utc_offset_hours)}
        />
      )}
      {justReady && growing === null ? <ReadyNote /> : null}
      {harvested === null || growing !== null ? null : <SavedNote note={harvested} />}
      {growing === null ? <SalesCard plotId={plot.id} /> : null}
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
          lastHarvest={latestLotOf(lots, outlook.crop)}
          onPlanted={growing === null ? () => plant(outlook) : null}
          growing={growing?.crop === outlook.crop}
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
              lastHarvest={latestLotOf(lots, outlook.crop)}
              onPlanted={growing === null ? () => plant(outlook) : null}
              growing={growing?.crop === outlook.crop}
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

/** The crop on the farm now: What to plant then shows the next sowing, with nothing to sow. */
export interface Growing {
  crop: string;
  sowingDate: string;
}

interface AdviceScreenProps {
  plot: FarmPlot;
  growing?: Growing | null;
  /** The harvest just saved, said once at the top. */
  harvested: HarvestNote | null;
  /** A crop was started: read the farmer's progress again, which opens the farm. */
  onPlanted: (cycle: StartedCycle) => void;
}

const phoneMs = () => Date.now();
/** Often enough for a step that lasts half a minute. */
const STEP_TICK_MS = 5_000;

/** While the farm's data builds: the steps, ticked off as the wait goes on. */
function Preparing() {
  const [since] = useState(phoneMs);
  const [now, setNow] = useState(since);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), STEP_TICK_MS);
    return () => window.clearInterval(timer);
  }, []);
  const current = siteStep(now - since);
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-5 px-6 text-center">
      <Icon name="satellite" size={56} className="text-primary" />
      <div className="flex flex-col gap-1.5">
        <h1 className="text-title-sm font-extrabold tracking-title">{en.advice.preparingTitle}</h1>
        <p className="text-body leading-snug text-ink-2">{en.advice.preparingDetail}</p>
      </div>
      {/* The bar moves on with each step; the list below says the same in words. */}
      <div aria-hidden="true" className="h-2.5 w-full max-w-80 overflow-hidden rounded-pill bg-divider">
        <div
          className="h-full rounded-pill bg-primary transition-[width] duration-700 ease-(--ease-calm)"
          style={{ width: `${Math.round(((Math.min(current, SITE_STEPS.length - 1) + 0.5) / SITE_STEPS.length) * 100)}%` }}
        />
      </div>
      <ol className="flex w-full max-w-80 flex-col gap-2 text-left">
        {SITE_STEPS.map((step, index) => {
          const state = index < current ? "done" : index === current ? "working" : "waiting";
          return (
            <li
              key={step}
              aria-current={state === "working" ? "step" : undefined}
              className={`flex min-h-12 items-center gap-3 rounded-control px-4 ${
                state === "working" ? "bg-surface font-extrabold" : "font-semibold"
              } ${state === "waiting" ? "text-ink-3" : "text-ink"}`}
            >
              {state === "done" ? (
                <Icon name="check" size={22} strokeWidth={2.8} className="shrink-0 animate-pop-in text-primary" />
              ) : (
                <Icon
                  name="hourglass"
                  size={22}
                  className={`shrink-0 ${state === "working" ? "animate-pulse text-primary" : ""}`}
                />
              )}
              <span className="flex-1 text-body">{en.site.steps[step]}</span>
              <span className="sr-only">{en.site[state]}</span>
            </li>
          );
        })}
      </ol>
      <p className="text-small text-ink-3">{en.advice.preparingAgain}</p>
    </main>
  );
}

/** What to sow on the farmer's own plot, from the planner (D079, D081), and the sowing confirmation (D083). */
export function AdviceScreen({ plot, harvested, onPlanted, growing = null }: AdviceScreenProps) {
  const advice = useAdvice(plot.id);
  // Seen waiting once: when the plan arrives, say the farm is ready.
  const [waited, setWaited] = useState(false);
  if (advice.status === "preparing" && !waited) setWaited(true);
  switch (advice.status) {
    case "loading":
      return <StateView icon="hourglass" title={en.advice.loadingPlan} />;
    case "preparing":
      return <Preparing />;
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
      return (
        <Advice
          plot={plot}
          plan={advice.plan}
          harvested={harvested}
          justReady={waited}
          onPlanted={onPlanted}
          growing={growing}
        />
      );
  }
}
