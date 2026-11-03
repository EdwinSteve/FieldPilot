import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { WeekDay } from "../view-models/types";
import { Icon, type IconName } from "./Icon";

interface Mark {
  icon: IconName;
  colour: string;
  /** Read out on each day; the key below says the same to the eye. */
  spoken: string;
  key: string;
}

const WATER: Mark = {
  icon: "drop",
  colour: "text-needs",
  spoken: en.today.weekDayWater,
  key: en.today.keyWater,
};
const RAIN: Mark = {
  icon: "cloudRain",
  colour: "text-undo-icon",
  spoken: en.today.weekDayRain,
  key: en.today.keyRain,
};
const SAID_NO: Mark = {
  icon: "close",
  colour: "text-ink-3",
  spoken: en.today.weekDaySaidNo,
  key: en.today.keySaidNo,
};

function marksOf(day: WeekDay): Mark[] {
  return [day.water ? WATER : null, day.rain ? RAIN : null, day.saidNo ? SAID_NO : null].filter(
    (mark) => mark !== null,
  );
}

function DayCell({ day }: { day: WeekDay }) {
  const marks = marksOf(day);
  const iconSize = marks.length > 1 ? 14 : 18;
  const box = day.today ? "bg-primary text-surface" : "bg-surface text-ink";
  const fill = day.today ? "bg-surface" : "bg-ground";
  return (
    <div className={`flex flex-col items-center gap-1.5 rounded-chip py-2.5 ${box}`}>
      <span className="text-caption font-bold">{day.day}</span>
      {/* A fixed slot keeps every day the same height, marked or not. */}
      <span className="flex size-7.5 items-center justify-center">
        {marks.length === 0 ? (
          // Nothing that day: a small dot, so it does not look like a missing icon.
          <span className={`size-1.5 rounded-full ${day.today ? "bg-surface" : "bg-border"}`} />
        ) : (
          <span className={`flex size-7.5 items-center justify-center rounded-full ${fill}`}>
            {marks.map((mark) => (
              <span key={mark.icon} className="contents">
                <Icon name={mark.icon} size={iconSize} strokeWidth={2.4} className={mark.colour} />
                <span className="sr-only">{mark.spoken}</span>
              </span>
            ))}
          </span>
        )}
      </span>
    </div>
  );
}

/** What the marks mean, for the marks this week shows only. */
function Key({ week }: { week: WeekDay[] }) {
  const shown = [WATER, RAIN, SAID_NO].filter((mark) =>
    week.some((day) => marksOf(day).includes(mark)),
  );
  if (shown.length === 0) return null;
  return (
    <div aria-hidden="true" className="flex flex-wrap items-center gap-x-4 gap-y-1 px-0.5">
      {shown.map((mark) => (
        <span key={mark.icon} className="inline-flex items-center gap-1.5 text-caption text-ink-2">
          <Icon name={mark.icon} size={16} strokeWidth={2.4} className={mark.colour} />
          {mark.key}
        </span>
      ))}
    </div>
  );
}

export function WeekStrip({ week }: { week: WeekDay[] }) {
  return (
    <a href={hrefOf({ screen: "plan" })} className="press flex flex-col gap-2.5 text-ink no-underline">
      <div className="flex min-h-8 items-center justify-between px-0.5">
        <h2 className="text-lead font-bold">{en.today.thisWeek}</h2>
        <span className="inline-flex items-center gap-1 text-small font-bold text-primary">
          {en.today.seePlan}
          <Icon name="forward" size={18} strokeWidth={2.6} />
        </span>
      </div>
      <div className="grid grid-cols-7 gap-1.25">
        {week.map((day) => (
          <DayCell key={day.day} day={day} />
        ))}
      </div>
      <Key week={week} />
    </a>
  );
}
