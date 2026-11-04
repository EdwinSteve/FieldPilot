import { lazy, Suspense, useRef, useState, type ReactNode } from "react";
import { findPlace, placeUnder } from "../api/geocode";
import { lifecycle } from "../api/lifecycle";
import { BigButton } from "../components/BigButton";
import type { MapLayer } from "../components/FarmMap";
import { Icon } from "../components/Icon";
import { SelectField, TextField } from "../components/TextField";
import { useFocusHeading } from "../hooks/useFocusHeading";
import { readDraft, saveDraft } from "../hooks/setupDraftStore";
import type { Farmer } from "../lib/account";
import { en } from "../i18n/en";
import { areaHectares, hectaresText, type LatLng } from "../lib/farmOutline";
import { GOALS, toggleGoal, type Goal } from "../lib/goals";
import { cropLabel } from "../lib/names";
import { hasProblem, newPlot, plotProblems } from "../lib/newPlot";
import { centreOf, departments, matchHome, townsOf, type Home } from "../lib/places";
import type { SetupDraft } from "../lib/setupDraft";
import { MAX_FARM_NAME, typedFarmName } from "../lib/typing";

// Leaflet is large and only this step needs it.
const FarmMap = lazy(() => import("../components/FarmMap"));

const STEPS = 3;
const DEPARTMENTS = departments();
/** The planner's crops (docs/api.md §9). */
const PLANNER_CROPS = ["maize", "common_bean", "sorghum", "soybean", "groundnut", "cotton", "tomato", "potato"];

/** A choice that stays chosen: a big tile with a tick, said as pressed or not. */
function ChoiceTile({
  pressed,
  onClick,
  badge,
  children,
}: {
  pressed: boolean;
  onClick: () => void;
  badge: ReactNode;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`press flex min-h-16 items-center gap-3 rounded-control border-2 px-4 py-3 text-left ${
        pressed ? "border-primary bg-tint" : "border-border bg-surface"
      }`}
    >
      <span
        aria-hidden="true"
        className={`flex size-8 shrink-0 items-center justify-center rounded-full text-small font-extrabold ${
          pressed ? "bg-primary text-surface" : "border-2 border-border bg-surface"
        }`}
      >
        {badge}
      </span>
      <span className="flex flex-col gap-0.5">{children}</span>
    </button>
  );
}

function StepHeader({ step, title, lead }: { step: number; title: string; lead: string }) {
  return (
    <div className="flex flex-col gap-1 px-0.5">
      <span className="text-small font-bold text-primary">{en.setup.step(step, STEPS)}</span>
      <h1 className="text-title font-extrabold tracking-title">{title}</h1>
      <span className="text-lead leading-snug text-ink-2">{lead}</span>
    </div>
  );
}

function CropsStep({ crops, onToggle }: { crops: string[]; onToggle: (crop: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {PLANNER_CROPS.map((crop) => (
        <ChoiceTile
          key={crop}
          pressed={crops.includes(crop)}
          onClick={() => onToggle(crop)}
          badge={crops.includes(crop) ? <Icon name="check" size={18} strokeWidth={3} /> : null}
        >
          <span className="text-row font-bold">{cropLabel(crop)}</span>
        </ChoiceTile>
      ))}
    </div>
  );
}

function GoalsStep({ goals, onToggle }: { goals: Goal[]; onToggle: (goal: Goal) => void }) {
  return (
    <div className="flex flex-col gap-2.5">
      {GOALS.map((goal) => {
        const rank = goals.indexOf(goal) + 1;
        return (
          <ChoiceTile key={goal} pressed={rank > 0} onClick={() => onToggle(goal)} badge={rank > 0 ? rank : null}>
            <span className="text-row font-bold">
              {en.setup.goals[goal]}
              {rank > 0 ? <span className="sr-only">, {en.setup.goalNumber(rank)}</span> : null}
            </span>
            <span className="text-small text-ink-2">{en.setup.goalDetails[goal]}</span>
          </ChoiceTile>
        );
      })}
    </div>
  );
}

interface MapStepProps {
  draft: SetupDraft;
  setDraft: (change: Partial<SetupDraft>) => void;
  /** The town chosen at sign-up: the map opens on it. */
  home: Home | null;
  tried: boolean;
  town: string;
  setTown: (town: string) => void;
  department: string;
  setDepartment: (department: string) => void;
}

function MapStep(props: MapStepProps) {
  const { draft, setDraft, home, tried, town, setTown, department, setDepartment } = props;
  const [query, setQuery] = useState("");
  const [finding, setFinding] = useState(false);
  const [findNote, setFindNote] = useState<string | null>(null);
  // A place the farmer searched for wins; then their corners; then the town they live in.
  const [picked, setPicked] = useState<LatLng | null>(null);
  const centre = picked ?? draft.outline[0] ?? (home === null ? null : centreOf(home));
  const [layer, setLayer] = useState<MapLayer>("photo");
  const addAtCentre = useRef<() => void>(() => undefined);
  const outline = draft.outline;
  const problems = plotProblems(outline, draft.farmName, town, department);
  const show = (problem: string | null, words: string) => (tried && problem !== null ? words : null);

  const find = async (text: string) => {
    if (text.trim() === "") return;
    setFinding(true);
    setFindNote(null);
    try {
      const place = await findPlace(text);
      if (place === null) {
        setFindNote(en.setup.notFound);
        return;
      }
      setPicked(place.point);
      // The farm is where the farmer looked: its town too, when the list has it.
      const match = matchHome(place.municipality, place.department);
      if (match !== null) {
        setDepartment(match.department);
        setTown(match.town);
      }
    } catch {
      setFindNote(en.setup.findFailed);
    } finally {
      setFinding(false);
    }
  };

  const add = (point: LatLng) => setDraft({ outline: [...outline, point] });
  const area = areaHectares(outline);

  return (
    <div className="flex flex-col gap-3.5">
      <form
        className="flex flex-col gap-2.5"
        onSubmit={(event) => {
          event.preventDefault();
          void find(query);
        }}
      >
        <TextField
          label={en.setup.find}
          value={query}
          onChange={setQuery}
          problem={findNote}
          placeholder={en.setup.findExample}
          maxLength={MAX_FARM_NAME}
          enterKeyHint="search"
        />
        <BigButton type="submit" variant="outline" size="compact" disabled={finding}>
          {finding ? en.setup.finding : en.setup.findButton}
        </BigButton>
      </form>

      <div className="flex gap-1.5 self-start rounded-pill bg-divider p-1">
        {(["photo", "map"] as const).map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={layer === option}
            onClick={() => setLayer(option)}
            className={`press min-h-12 rounded-pill border-0 px-4.5 text-small font-bold ${
              layer === option ? "bg-surface text-ink shadow-bubble-soft" : "bg-transparent text-ink-2"
            }`}
          >
            {option === "photo" ? en.setup.photo : en.setup.plainMap}
          </button>
        ))}
      </div>

      <Suspense
        fallback={
          <div className="flex h-80 items-center justify-center rounded-tile bg-divider text-body text-ink-2">
            {en.setup.mapLoading}
          </div>
        }
      >
        <FarmMap
          centre={centre}
          outline={outline}
          layer={layer}
          onAdd={add}
          onReady={(callback) => {
            addAtCentre.current = callback;
          }}
        />
      </Suspense>

      <p className="px-0.5 text-caption leading-snug text-ink-3">{en.setup.addCornerHint}</p>
      <BigButton variant="primary" size="compact" onClick={() => addAtCentre.current()}>
        <Icon name="plus" size={22} strokeWidth={2.6} />
        {en.setup.addCorner}
      </BigButton>
      <div className="grid grid-cols-2 gap-2.5">
        <BigButton
          variant="undo"
          size="compact"
          disabled={outline.length === 0}
          onClick={() => setDraft({ outline: outline.slice(0, -1) })}
        >
          <Icon name="undo" size={20} />
          {en.setup.undoCorner}
        </BigButton>
        <BigButton
          variant="outline"
          size="compact"
          disabled={outline.length === 0}
          onClick={() => setDraft({ outline: [] })}
        >
          {en.setup.clear}
        </BigButton>
      </div>

      <p aria-live="polite" className="flex items-center justify-between rounded-control bg-surface px-4 py-3 text-body">
        <span className="font-bold">{en.setup.corners(outline.length)}</span>
        {area > 0 ? <span>{en.setup.area(hectaresText(area))}</span> : null}
      </p>
      {tried && problems.outline !== null ? (
        <p role="alert" className="flex items-center gap-2 px-0.5 text-small font-bold text-bad-text">
          <Icon name="warning" size={18} strokeWidth={2.4} className="shrink-0" />
          {en.setup.outline[problems.outline]}
        </p>
      ) : null}

      <TextField
        label={en.setup.farmName}
        value={draft.farmName}
        onChange={(farmName) => setDraft({ farmName: typedFarmName(farmName) })}
        problem={show(problems.name, en.setup.farmNameMissing)}
        placeholder={en.setup.farmNameExample}
        autoComplete="off"
        autoCapitalize="words"
      />
      <SelectField
        label={en.auth.department}
        hint={en.setup.placeHint}
        value={department}
        onChange={(value) => {
          setDepartment(value);
          setTown("");
        }}
        options={DEPARTMENTS}
        choose={en.auth.chooseDepartment}
        problem={show(problems.department, en.setup.placeMissing)}
      />
      <SelectField
        label={en.auth.town}
        value={town}
        onChange={setTown}
        options={townsOf(department)}
        choose={department === "" ? en.auth.chooseDepartmentFirst : en.auth.chooseTown}
        problem={show(problems.town, en.setup.placeMissing)}
        disabled={department === ""}
      />
    </div>
  );
}

interface SetupScreenProps {
  farmer: Farmer;
  home: Home | null;
  /** The plot is saved: read the farmer's progress again. */
  onSaved: () => void;
}

/** First run: what the farmer grows, what they want most, and where the farm is. */
export function SetupScreen({ farmer, home, onSaved }: SetupScreenProps) {
  const [draft, setDraftState] = useState<SetupDraft>(() => {
    const stored = readDraft();
    return stored.farmName === "" ? { ...stored, farmName: en.setup.farmNameDefault(farmer.name) } : stored;
  });
  const [step, setStep] = useState(0);
  /** Which way the last move went, so the new step slides in from that side. */
  const [moved, setMoved] = useState<"forward" | "back">("forward");
  const go = (next: number) => {
    setMoved(next > step ? "forward" : "back");
    setStep(next);
  };
  // Where the farmer lives, until the map or the farmer says the farm is elsewhere.
  const [town, setTown] = useState(home?.town ?? "");
  const [department, setDepartment] = useState(home?.department ?? "");
  const [tried, setTried] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);
  const heading = useRef<HTMLDivElement>(null);

  const setDraft = (change: Partial<SetupDraft>) =>
    setDraftState((current) => {
      const next = { ...current, ...change };
      saveDraft(next);
      return next;
    });

  // A new step is a new screen to a screen reader: its heading takes focus.
  useFocusHeading(String(step), heading);

  const save = async () => {
    setTried(true);
    setSaveFailed(false);
    let placeTown = town;
    let placeDepartment = department;
    const middle = draft.outline[0];
    if ((placeTown === "" || placeDepartment === "") && middle !== undefined) {
      // The map's corners say where the farm is; Nominatim names the place, the list spells it.
      const place = await placeUnder(middle).catch(() => null);
      const match = place === null ? null : matchHome(place.municipality, place.department);
      placeTown ||= match?.town ?? "";
      placeDepartment ||= match?.department ?? "";
      setTown(placeTown);
      setDepartment(placeDepartment);
    }
    if (hasProblem(plotProblems(draft.outline, draft.farmName, placeTown, placeDepartment))) return;
    setSaving(true);
    try {
      await lifecycle.createPlot(newPlot(draft.outline, draft.farmName, placeTown, placeDepartment));
      onSaved();
    } catch {
      setSaveFailed(true);
    } finally {
      setSaving(false);
    }
  };

  const content = [
    {
      title: en.setup.cropsTitle,
      lead: en.setup.cropsLead,
      body: (
        <CropsStep
          crops={draft.crops}
          onToggle={(crop) =>
            setDraft({
              crops: draft.crops.includes(crop)
                ? draft.crops.filter((chosen) => chosen !== crop)
                : [...draft.crops, crop],
            })
          }
        />
      ),
    },
    {
      title: en.setup.goalsTitle,
      lead: en.setup.goalsLead,
      body: <GoalsStep goals={draft.goals} onToggle={(goal) => setDraft({ goals: toggleGoal(draft.goals, goal) })} />,
    },
    {
      title: en.setup.mapTitle,
      lead: en.setup.mapLead,
      body: (
        <MapStep
          draft={draft}
          setDraft={setDraft}
          home={home}
          tried={tried}
          town={town}
          setTown={setTown}
          department={department}
          setDepartment={setDepartment}
        />
      ),
    },
  ][step];
  if (content === undefined) return null;
  const last = step === STEPS - 1;

  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4.5 overflow-y-auto px-4.5 pt-7 pb-6">
      <div
        key={step}
        className={`flex flex-col gap-4.5 ${moved === "forward" ? "animate-step-forward" : "animate-step-back"}`}
      >
        <div ref={heading}>
          <StepHeader step={step + 1} title={content.title} lead={content.lead} />
        </div>
        {content.body}
      </div>
      {saveFailed ? (
        <p role="alert" className="rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text">
          {en.setup.saveFailed}
        </p>
      ) : null}
      <div className="mt-auto flex flex-col gap-2.5 pt-2">
        <BigButton
          variant="primary"
          size="large"
          disabled={saving}
          onClick={() => (last ? void save() : go(step + 1))}
        >
          {last ? (saving ? en.setup.saving : en.setup.analyse) : en.setup.next}
          {last ? null : <Icon name="forward" size={22} strokeWidth={2.6} />}
        </BigButton>
        {step === 0 ? null : (
          <BigButton variant="outline" size="compact" onClick={() => go(step - 1)}>
            {en.setup.back}
          </BigButton>
        )}
      </div>
    </main>
  );
}
