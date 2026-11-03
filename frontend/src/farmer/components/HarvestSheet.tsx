import { useState } from "react";
import { lifecycle } from "../api/lifecycle";
import { readHarvestDefaults } from "../hooks/harvestDefaultsStore";
import { en } from "../i18n/en";
import {
  BAG_PRESETS,
  GRADES,
  harvestFailure,
  harvestKg,
  harvestProblems,
  hasProblem,
  kgText,
  typedAmount,
  type Grade,
  type HarvestFailure,
  type Unit,
} from "../lib/harvest";
import { bagChoiceOf, openingUnit } from "../lib/harvestDefaults";
import { cropLabel } from "../lib/names";
import { hrefOf } from "../lib/route";
import type { HarvestInfo } from "../view-models/types";
import { BigButton, BigLink } from "./BigButton";
import { Choices } from "./Choices";
import { Icon } from "./Icon";
import { Sheet } from "./Sheet";
import { TextField } from "./TextField";

/** What the shell is told once the harvest is saved, for the next screen's note. */
export interface HarvestNote {
  crop: string;
  kg: number;
}

function Problem({ text }: { text: string | null }) {
  if (text === null) return null;
  return (
    <p className="flex items-center gap-2 px-0.5 text-small font-bold text-bad-text">
      <Icon name="warning" size={18} strokeWidth={2.4} className="shrink-0" />
      {text}
    </p>
  );
}

const OTHER = "other";

interface HarvestSheetProps {
  info: HarvestInfo;
  onClose: () => void;
  onSaved: (note: HarvestNote) => void;
}

/** "I've harvested it": the day, how much in kilos or the farmer's own bags, and the quality. */
export function HarvestSheet({ info, onClose, onSaved }: HarvestSheetProps) {
  const [date, setDate] = useState(info.today);
  // Opens on how the farmer said they count a harvest, in Settings.
  const [usual] = useState(() => {
    const defaults = readHarvestDefaults();
    return { unit: openingUnit(defaults.unit), ...bagChoiceOf(defaults.bagKg) };
  });
  const [unit, setUnit] = useState<Unit | null>(usual.unit);
  const [amount, setAmount] = useState("");
  const [bagChoice, setBagChoice] = useState<number | typeof OTHER>(usual.choice);
  const [bagOther, setBagOther] = useState(usual.other);
  const [grade, setGrade] = useState<Grade | null>(null);
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<HarvestFailure | null>(null);

  const bagKg = bagChoice === OTHER ? bagOther : String(bagChoice);
  const form = { date, amount, unit, bagKg, grade };
  const problems = harvestProblems(form, info);
  const kg = harvestKg(form);
  const name = cropLabel(info.crop);
  const show = <T,>(problem: T | null, words: (problem: T) => string) =>
    tried && problem !== null ? words(problem) : null;

  const save = async () => {
    setTried(true);
    setFailure(null);
    if (hasProblem(problems) || grade === null) return;
    setBusy(true);
    try {
      await lifecycle.harvest(info.cycleId, {
        harvested_on: date,
        quantity_kg: Number(kg.toFixed(1)),
        grade,
      });
      onSaved({ crop: name, kg });
    } catch (caught) {
      setFailure(harvestFailure(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet label={en.harvest.title(name)} onClose={onClose}>
      <h2 className="text-head font-extrabold tracking-key">{en.harvest.title(name)}</h2>
      {/* The backend refuses a harvest while work is open (D083 §6): say it before the farmer fills in the form. */}
      {info.openTask === null ? null : (
        <div className="flex flex-col gap-2 rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text">
          {info.openTask.decision ? en.harvest.openDecision : en.harvest.openWatering}
          {info.openTask.decision ? (
            <BigLink variant="outline" size="compact" href={hrefOf({ screen: "decide", taskId: info.openTask.id })}>
              {en.harvest.seeDecision}
            </BigLink>
          ) : null}
        </div>
      )}

      <label className="flex flex-col gap-2">
        <span className="px-0.5 text-body font-bold text-ink-2">{en.harvest.when}</span>
        <input
          type="date"
          value={date}
          min={info.sowingDate}
          max={info.today}
          aria-invalid={tried && problems.date !== null}
          onChange={(event) => setDate(event.target.value)}
          className="min-h-16 rounded-control border-2 border-border bg-surface px-4 text-row text-ink"
        />
      </label>
      <Problem text={show(problems.date, (p) => en.harvest.problems.date[p])} />

      <fieldset className="flex flex-col gap-3 border-0 p-0">
        <legend className="px-0.5 pb-2 text-body font-bold text-ink-2">{en.harvest.howMuch}</legend>
        <Choices
          options={["bags", "kg"] as const}
          chosen={unit}
          label={(option) => en.harvest.units[option]}
          icon={(option) => (option === "bags" ? "bag" : "scale")}
          onChoose={setUnit}
        />
        <Problem text={show(problems.unit, () => en.harvest.problems.unit)} />
        {/* Asked each time: the amount waits until the farmer says bags or kilos. */}
        {unit === null ? null : (
          <TextField
            label={unit === "bags" ? en.harvest.amountBags : en.harvest.amountKg}
            value={amount}
            onChange={(value) => setAmount(typedAmount(value))}
            problem={show(problems.amount, (p) => en.harvest.problems.amount[p])}
            inputMode="decimal"
            autoComplete="off"
          />
        )}
        {unit === "bags" ? (
          <div className="flex flex-col gap-2.5">
            <span className="px-0.5 text-body font-bold text-ink-2">{en.harvest.bagSize}</span>
            <Choices
              options={[...BAG_PRESETS, OTHER] as const}
              chosen={bagChoice}
              label={(option) => (option === OTHER ? en.harvest.bagOther : en.harvest.bagPreset(option))}
              onChoose={setBagChoice}
            />
            {bagChoice === OTHER ? (
              <TextField
                label={en.harvest.bagOtherLabel}
                value={bagOther}
                onChange={(value) => setBagOther(typedAmount(value))}
                problem={show(problems.bag, () => en.harvest.problems.bag)}
                inputMode="decimal"
                autoComplete="off"
              />
            ) : null}
          </div>
        ) : null}
        {Number.isFinite(kg) && kg > 0 ? (
          <p aria-live="polite" className="rounded-control bg-tint px-4 py-3 text-body font-extrabold text-primary-hover">
            {unit === "bags"
              ? en.harvest.total(amount, bagKg, kgText(kg))
              : en.harvest.totalKg(kgText(kg))}
          </p>
        ) : null}
      </fieldset>

      <fieldset className="flex flex-col gap-2 border-0 p-0">
        <legend className="px-0.5 pb-2 text-body font-bold text-ink-2">{en.harvest.quality}</legend>
        {GRADES.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={option === grade}
            onClick={() => setGrade(option)}
            className={`press flex min-h-14 flex-col items-start justify-center rounded-control border-2 px-4 py-2 text-left ${
              option === grade ? "border-primary bg-tint" : "border-border bg-surface"
            }`}
          >
            <span className="text-row font-bold">{en.harvest.grades[option]}</span>
            <span className="text-small text-ink-2">{en.harvest.gradeDetails[option]}</span>
          </button>
        ))}
      </fieldset>
      <Problem text={show(problems.grade, () => en.harvest.problems.grade)} />

      {failure === null ? null : (
        <div role="alert" className="flex flex-col gap-2 rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text">
          {en.harvest.failures[failure]}
        </div>
      )}
      <BigButton variant="primary" disabled={busy || info.openTask !== null} onClick={() => void save()}>
        {busy ? en.harvest.saving : en.harvest.save}
      </BigButton>
      <BigButton variant="outline" size="compact" onClick={onClose}>
        {en.harvest.cancel}
      </BigButton>
    </Sheet>
  );
}
