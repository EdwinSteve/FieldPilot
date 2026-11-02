import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { WeekDay } from "../view-models/types";
import { Icon } from "./Icon";

function DayCell({ day }: { day: WeekDay }) {
  const box = day.today ? "bg-primary text-surface" : "bg-surface text-ink";
  const dot = day.today ? "bg-surface" : "bg-ground";
  return (
    <div className={`flex flex-col items-center gap-1.5 rounded-chip py-2.5 ${box}`}>
      <span className="text-caption font-bold">{day.day}</span>
      <span className={`flex size-7.5 items-center justify-center rounded-full ${dot}`}>
        {day.water ? (
          <>
            <Icon name="drop" size={18} strokeWidth={2.4} className="text-needs" />
            <span className="sr-only">{en.today.weekDayWater}</span>
          </>
        ) : null}
        {day.rain ? (
          <>
            <Icon name="cloudRain" size={18} strokeWidth={2.4} className="text-undo-icon" />
            <span className="sr-only">{en.today.weekDayRain}</span>
          </>
        ) : null}
      </span>
    </div>
  );
}

export function WeekStrip({ week }: { week: WeekDay[] }) {
  return (
    <a href={hrefOf({ screen: "plan" })} className="flex flex-col gap-2.5 text-ink no-underline">
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
    </a>
  );
}
