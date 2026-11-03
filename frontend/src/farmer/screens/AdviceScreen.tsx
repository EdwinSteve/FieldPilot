import { useState } from "react";
import { api } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { lifecycle, type CropOutlook, type FarmPlot, type PlantingPlan } from "../api/lifecycle";
import { BigButton } from "../components/BigButton";
import { Chip } from "../components/Chip";
import { Icon } from "../components/Icon";
import { MonthTable, YieldBars } from "../components/PlanCharts";
import { Sheet } from "../components/Sheet";
import { StateView } from "../components/StateView";
import { readDraft } from "../hooks/setupDraftStore";
import { useAdvice } from "../hooks/useAdvice";
import { en } from "../i18n/en";
import { formatCalendarDate } from "../lib/farmTime";
import { orderForGoals, RECOMMENDED, type Goal } from "../lib/goals";
import { cropLabel, farmLabel } from "../lib/names";
import { monthGrid, nothingGrowsWell, percent, weekOf } from "../lib/plantingPlan";
import { earliestSowing, plotToday, sowingDateProblem } from "../lib/sowingDate";
import { startFailure, type StartFailure } from "../lib/startFailure";

/** The planner's "no network" model id (D079). */
const BASELINE_MODEL = "b0-climatology";

/** The phone's own clock, read only when the farmer taps. */
function phoneNow(): string {
  return new Date().toISOString();
}

const loadClock = () => api.clock();

function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-caption text-ink-2">{label}</span>
      <span className="text-body font-extrabold">{value}</span>
      {detail === undefined ? null : <span className="text-caption text-ink-3">{detail}</span>}
    </div>
  );
}

interface CropCardProps {
  outlook: CropOutlook;
  recommended: boolean;
  bestFor: Goal | null;
  grown: boolean;
  onPlanted: () => void;
}

function CropCard({ outlook, recommended, bestFor, grown, onPlanted }: CropCardProps) {
  const name = cropLabel(outlook.crop);
  return (
    <article className="flex flex-col gap-3.5 rounded-card bg-surface p-4.5">
      <div className="flex flex-col gap-2">
        <h3 className="text-head font-extrabold tracking-key">{name}</h3>
        <div className="flex flex-wrap gap-1.5">
          {recommended ? <Chip tone="good">{en.advice.recommended}</Chip> : null}
          {bestFor === null ? null : (
            <Chip tone="undo">{en.advice.bestFor(en.setup.goals[bestFor])}</Chip>
          )}
          {grown ? <Chip tone="neutral">{en.advice.youGrow}</Chip> : null}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-3">
        <Metric
          label={en.advice.expected}
          value={en.advice.expectedValue(percent(outlook.rel_yield_p50))}
          detail={en.advice.range(percent(outlook.rel_yield_p10), percent(outlook.rel_yield_p90))}
        />
        <Metric
          label={en.advice.success}
          value={en.advice.successValue(Math.round(outlook.p_success * 10))}
        />
        <Metric
          label={en.advice.water}
          value={en.advice.waterValue(Math.round(outlook.irrigation_mm_p50))}
        />
        <Metric label={en.advice.harvest} value={formatCalendarDate(outlook.harvest_date)} />
      </div>
      <span className="flex items-center gap-2 text-small font-bold text-ink-2">
        <Icon name={outlook.automatable ? "drop" : "info"} size={20} className="shrink-0" />
        {outlook.automatable ? en.advice.automatic : en.advice.manual}
      </span>
      <BigButton variant="primary" size="compact" onClick={onPlanted}>
        {en.advice.planted}
      </BigButton>
    </article>
  );
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
      // Stage 2 takes over: its first daily check starts now, not tomorrow morning.
      if (cycle.automated) void api.dailyCycle(plot.id).catch(() => null);
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
          <p className="text-body leading-snug">{en.advice.ownRisk(top)}</p>
          <BigButton variant="needs" disabled={busy} onClick={() => void start(true)}>
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

function Advice({ plot, plan, onPlanted }: { plot: FarmPlot; plan: PlantingPlan; onPlanted: () => void }) {
  const [draft] = useState(readDraft);
  const [weekIndex, setWeekIndex] = useState(0);
  const [planting, setPlanting] = useState<Planting | null>(null);
  const clock = useResource(loadClock, 0);
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
      <div className="flex flex-col gap-1 px-0.5">
        <h1 className="text-title font-extrabold tracking-title">{en.advice.title}</h1>
        <span className="text-lead leading-snug text-ink-2">{en.advice.lead(farmLabel(plot.name))}</span>
      </div>
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
      <YieldBars outlooks={week.outlooks} />
      <MonthTable grid={monthGrid(plan)} />
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
  /** A crop was started: read the farmer's progress again, which opens the farm. */
  onPlanted: () => void;
}

/** What to sow on the farmer's own plot, from the planner (D079, D081), and the sowing confirmation (D083). */
export function AdviceScreen({ plot, onPlanted }: AdviceScreenProps) {
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
      return <Advice plot={plot} plan={advice.plan} onPlanted={onPlanted} />;
  }
}
