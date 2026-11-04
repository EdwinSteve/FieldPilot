import { useState } from "react";
import type { PlantingPlan } from "../api/lifecycle";
import { en } from "../i18n/en";
import { smoothBars, stripCrops, weekStrip, type WeekMark, type WeekStrip } from "../lib/cropAdvice";
import { formatCalendarDate } from "../lib/farmTime";
import { cropLabel } from "../lib/names";
import { CropArt } from "./CropArt";
import { Icon } from "./Icon";

/** Height and colour both say how good a week is, so it reads without colour too. */
const BAR: Record<WeekMark, string> = {
  good: "bg-field",
  fair: "bg-needs",
  poor: "bg-bad",
};
/** Even a week with no harvest keeps a stub, so the row never has gaps. */
const MIN_HEIGHT = 12;

function bestText(strip: WeekStrip): string {
  if (strip.best === null) return en.advice.noGoodTime;
  const week = strip.weeks[strip.best];
  return en.advice.bestTime(strip.best === 0 || week === undefined ? null : formatCalendarDate(week.date));
}

function monthOf(isoDate: string): string {
  return en.time.months[Number(isoDate.slice(5, 7)) - 1] ?? "";
}

function BestTick() {
  return (
    <span className="flex size-5 items-center justify-center rounded-full bg-primary text-surface">
      <Icon name="check" size={14} strokeWidth={3.2} />
    </span>
  );
}

function StripRow({ strip }: { strip: WeekStrip }) {
  const count = (mark: WeekMark) => strip.weeks.filter((week) => week.mark === mark).length;
  const name = cropLabel(strip.crop);
  return (
    <li
      aria-label={en.advice.stripLabel(name, bestText(strip), count("good"), count("fair"), count("poor"))}
      className="flex flex-col gap-2 rounded-tile border border-divider bg-ground p-3.5"
    >
      {/* Each crop is its own tile, headed by its picture, so the rows never run together. */}
      <span aria-hidden="true" className="flex items-center gap-3 border-b border-divider pb-2.5">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-surface">
          <CropArt crop={strip.crop} size={32} />
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="text-row font-bold">{name}</span>
          <span className={`text-small font-bold ${strip.best === null ? "text-bad-text" : "text-primary"}`}>
            {bestText(strip)}
          </span>
        </span>
      </span>
      <span aria-hidden="true" className="flex w-full gap-[3px]">
        {smoothBars(strip).map((bar, index) => {
          const week = bar.week === null ? undefined : strip.weeks[bar.week];
          const before = bar.week === null ? undefined : strip.weeks[bar.week - 1];
          // The month under its first week, so the row reads as a calendar.
          const month =
            week !== undefined && (before === undefined || monthOf(week.date) !== monthOf(before.date))
              ? monthOf(week.date)
              : "";
          return (
            <span key={index} className="relative flex min-w-0 flex-1 flex-col items-center gap-1">
              {/* The tick sits over the soonest good week; the space stays for every bar. */}
              <span className="relative flex h-5 w-full justify-center">
                {bar.week !== null && bar.week === strip.best ? (
                  <span className="absolute bottom-0">
                    <BestTick />
                  </span>
                ) : null}
              </span>
              <span className="flex h-14 w-full items-end">
                <span
                  className={`block w-full rounded-full ${BAR[bar.mark]}`}
                  style={{ height: `${Math.max(MIN_HEIGHT, Math.round(bar.yield * 100))}%` }}
                />
              </span>
              <span className="relative h-4.5 w-full">
                {month === "" ? null : (
                  <span className="absolute left-0 text-caption leading-none whitespace-nowrap text-ink-3">
                    {month}
                  </span>
                )}
              </span>
            </span>
          );
        })}
      </span>
    </li>
  );
}

function Key() {
  return (
    <div aria-hidden="true" className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-caption text-ink-2">
      {(["good", "fair", "poor"] as const).map((mark) => (
        <span key={mark} className="inline-flex items-center gap-1.5">
          <span className={`block h-4 w-1.5 rounded-full ${BAR[mark]}`} />
          {en.advice.marks[mark]}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5">
        <BestTick />
        {en.advice.bestMark}
      </span>
    </div>
  );
}

/** When to sow: the farmer's own crops, one row of week bars each, the best week ticked. */
export function SowingStrips({ plan, grown }: { plan: PlantingPlan; grown: readonly string[] }) {
  const [showOthers, setShowOthers] = useState(false);
  const { mine, others } = stripCrops(plan, grown);
  return (
    <section className="flex shrink-0 flex-col gap-4 rounded-card bg-surface p-4.5">
      <div className="flex flex-col gap-1">
        <h2 className="text-lead font-bold">{en.advice.stripTitle}</h2>
        <p className="text-caption leading-snug text-ink-2">{en.advice.stripLead}</p>
      </div>
      <Key />
      <ul className="flex flex-col gap-3">
        {mine.map((crop) => (
          <StripRow key={crop} strip={weekStrip(plan, crop)} />
        ))}
      </ul>
      {others.length === 0 ? null : (
        <>
          <button
            type="button"
            aria-expanded={showOthers}
            onClick={() => setShowOthers((current) => !current)}
            className="press flex min-h-12 items-center justify-center gap-2 rounded-control border-2 border-border bg-surface text-small font-bold text-ink"
          >
            {showOthers ? en.advice.hideOthers : en.advice.showOthers}
            <Icon
              name="chevronDown"
              size={20}
              strokeWidth={2.4}
              className={`transition-transform duration-300 ease-(--ease-calm) ${showOthers ? "rotate-180" : ""}`}
            />
          </button>
          {showOthers ? (
            <ul className="flex animate-screen-in flex-col gap-3">
              {others.map((crop) => (
                <StripRow key={crop} strip={weekStrip(plan, crop)} />
              ))}
            </ul>
          ) : null}
        </>
      )}
    </section>
  );
}
