import type { ReactNode } from "react";
import type { CropOutlook, Lot } from "../api/lifecycle";
import { en } from "../i18n/en";
import {
  cause,
  chance,
  harvestSize,
  verdict,
  waterNeed,
  type Chance,
  type HarvestSize,
  type Verdict,
  type WaterNeed,
} from "../lib/cropAdvice";
import { formatCalendarDate } from "../lib/farmTime";
import type { Goal } from "../lib/goals";
import { kgText } from "../lib/harvest";
import { cropLabel } from "../lib/names";
import { percent } from "../lib/plantingPlan";
import { BigButton } from "./BigButton";
import { Chip } from "./Chip";
import { CropArt } from "./CropArt";
import { Icon, PlantIcon, type IconName } from "./Icon";

type Tone = "good" | "okay" | "poor";

/** One colour per meaning, as everywhere in the app: green good, amber watch, red problem. */
const TINT: Record<Tone, string> = {
  good: "bg-tint text-primary-hover",
  okay: "bg-needs-tint text-needs-text",
  poor: "bg-bad-tint text-bad-text",
};
const INK: Record<Tone, string> = {
  good: "text-primary",
  okay: "text-needs-icon",
  poor: "text-bad",
};
const BAND_ICON: Record<Verdict, IconName> = { good: "check", okay: "info", poor: "warning" };
const VERDICT_TONE: Record<Verdict, Tone> = { good: "good", okay: "okay", poor: "poor" };
const HARVEST_TONE: Record<HarvestSize, Tone> = { big: "good", medium: "okay", small: "poor" };
const CHANCE_TONE: Record<Chance, Tone> = { very_likely: "good", maybe: "okay", risky: "poor" };
const WATER_TONE: Record<WaterNeed, Tone> = { little: "good", some: "okay", a_lot: "poor" };

interface TileProps {
  tone: Tone;
  icon: ReactNode;
  label?: string;
  word: string;
  proof: string;
}

/** One of the two facts that decide: a tinted tile, the word large, its number under it. */
function Tile({ tone, icon, label, word, proof }: TileProps) {
  return (
    <div className={`flex flex-col gap-1.5 rounded-tile p-3.5 ${TINT[tone]}`}>
      <span className="flex items-center gap-1.5 text-caption font-bold">
        {icon}
        {label}
      </span>
      <span className="text-key leading-tight font-extrabold">{word}</span>
      <span className="text-caption leading-tight">{proof}</span>
    </div>
  );
}

/** A lesser fact: one line, its icon coloured by how good it is. */
function Line({ icon, tone, children }: { icon: IconName; tone: Tone | null; children: ReactNode }) {
  return (
    <p className="flex items-start gap-2.5 text-body leading-snug">
      <Icon name={icon} size={22} className={`mt-0.5 shrink-0 ${tone === null ? "text-ink-2" : INK[tone]}`} />
      <span>{children}</span>
    </p>
  );
}

function reasonOf(outlook: CropOutlook): string {
  const why = cause(outlook);
  if (why === null) return en.advice.goodReasons[waterNeed(outlook)];
  const words = en.advice.causes[why];
  return verdict(outlook) === "okay" ? `${en.advice.okayLead} ${words}` : words;
}

interface CropCardProps {
  outlook: CropOutlook;
  recommended: boolean;
  bestFor: Goal | null;
  grown: boolean;
  /** The farm's own last harvest of this crop: its result beside the forecast. */
  lastHarvest: Lot | null;
  onPlanted: () => void;
}

/** A crop for this sowing week: its picture and verdict first, the two facts that decide, then the rest. */
export function CropCard({ outlook, recommended, bestFor, grown, lastHarvest, onPlanted }: CropCardProps) {
  const name = cropLabel(outlook.crop);
  const judged = verdict(outlook);
  const tone = VERDICT_TONE[judged];
  const size = harvestSize(outlook);
  const likely = chance(outlook);
  const water = waterNeed(outlook);
  return (
    <article className="flex shrink-0 flex-col overflow-hidden rounded-card bg-surface">
      <p className={`flex items-center gap-2 px-4.5 py-2.5 text-small font-extrabold ${TINT[tone]}`}>
        <Icon name={BAND_ICON[judged]} size={20} strokeWidth={2.6} className="shrink-0" />
        {en.advice.verdicts[judged]}
      </p>
      <div className="flex flex-col gap-4 p-4.5 pt-4">
        <div className="flex items-center gap-3.5">
          <span className={`relative flex size-20 shrink-0 items-center justify-center rounded-card ${TINT[tone]}`}>
            <CropArt crop={outlook.crop} size={60} />
            {recommended ? (
              <span className="absolute -top-1.5 -right-1.5 flex size-7 items-center justify-center rounded-full border-3 border-surface bg-primary text-surface">
                <Icon name="check" size={16} strokeWidth={3.2} />
              </span>
            ) : null}
          </span>
          <div className="flex min-w-0 flex-col gap-1">
            <h3 className="text-head font-extrabold tracking-key">{name}</h3>
            {recommended ? (
              <span className="flex items-center gap-1.5 text-small font-extrabold text-primary">
                <Icon name="check" size={18} strokeWidth={3} />
                {en.advice.recommended}
              </span>
            ) : null}
          </div>
        </div>
        <p className="text-body leading-snug">{reasonOf(outlook)}</p>
        <div className="grid grid-cols-2 gap-2.5">
          <Tile
            tone={HARVEST_TONE[size]}
            icon={<PlantIcon size={18} />}
            label={en.advice.harvestLabel}
            word={en.advice.harvestWords[size]}
            proof={en.advice.harvestProof(percent(outlook.rel_yield_p50))}
          />
          <Tile
            tone={CHANCE_TONE[likely]}
            icon={<Icon name="shield" size={18} strokeWidth={2.4} />}
            word={en.advice.chanceWords[likely]}
            proof={en.advice.chanceProof(Math.round(outlook.p_success * 10))}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Line icon="drop" tone={WATER_TONE[water]}>
            <b className="font-extrabold">{en.advice.waterWords[water]}</b>
            {" · "}
            {en.advice.waterProof(Math.round(outlook.irrigation_mm_p50))}
          </Line>
          <Line icon="calendar" tone={null}>
            {en.advice.readyLabel} <b className="font-extrabold">{formatCalendarDate(outlook.harvest_date)}</b>
          </Line>
          {lastHarvest === null ? null : (
            <Line icon="bag" tone={null}>
              {en.harvest.lastTime(
                kgText(lastHarvest.quantity_kg),
                en.harvest.grades[lastHarvest.grade],
                formatCalendarDate(lastHarvest.harvested_on),
              )}
            </Line>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {bestFor === null ? null : (
            <Chip tone="undo">{en.advice.bestFor(en.setup.goals[bestFor])}</Chip>
          )}
          {grown ? <Chip tone="neutral">{en.advice.youGrow}</Chip> : null}
          <Chip tone="neutral">
            <Icon name={outlook.automatable ? "drop" : "info"} size={16} strokeWidth={2.4} />
            {outlook.automatable ? en.advice.automatic : en.advice.manual}
          </Chip>
        </div>
        <BigButton variant="primary" size="compact" onClick={onPlanted}>
          {en.advice.planted}
        </BigButton>
        <details className="group">
          <summary className="flex min-h-12 cursor-pointer list-none items-center gap-1.5 text-small font-bold text-ink-2">
            {en.advice.moreDetails}
            <Icon name="chevronDown" size={18} strokeWidth={2.4} className="group-open:rotate-180" />
          </summary>
          <div className="flex flex-col gap-1 pt-1 text-small leading-snug text-ink-2">
            <p>{en.advice.rangeDetail(percent(outlook.rel_yield_p10), percent(outlook.rel_yield_p90))}</p>
            <p>{en.advice.stressDetail(Math.round(outlook.heat_days), Math.round(outlook.cold_days))}</p>
          </div>
        </details>
      </div>
    </article>
  );
}
