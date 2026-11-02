import { en } from "../i18n/en";
import { moistureBarScale } from "../lib/soilFill";
import type { SoilReading } from "../view-models/types";

export function MoistureBar({ value, fieldCapacity }: SoilReading) {
  const { valuePct, fullPct } = moistureBarScale(value, fieldCapacity);
  return (
    <div aria-hidden="true" className="flex flex-col gap-3.5">
      <div className="relative h-5.5 rounded-full bg-divider">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-needs"
          style={{ width: `${valuePct}%` }}
        />
        <div
          className="absolute -inset-y-1.5 w-1 rounded-full bg-primary"
          style={{ left: `${fullPct}%` }}
        />
      </div>
      <div className="relative h-5 text-caption font-bold">
        <span className="absolute left-0 text-ink-3">{en.zone.zeroPercent}</span>
        <span
          className="absolute -translate-x-1/2 whitespace-nowrap text-primary"
          style={{ left: `${fullPct}%` }}
        >
          {en.soil.fullAt(fieldCapacity)}
        </span>
      </div>
    </div>
  );
}
