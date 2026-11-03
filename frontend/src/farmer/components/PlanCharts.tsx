import type { CropOutlook } from "../api/lifecycle";
import { en } from "../i18n/en";
import { cropLabel } from "../lib/names";
import { percent, yieldLevel, type MonthGrid, type YieldLevel } from "../lib/plantingPlan";

const BAR: Record<YieldLevel, string> = {
  good: "bg-field",
  fair: "bg-needs",
  poor: "bg-bad",
};

const CELL: Record<YieldLevel, string> = {
  good: "bg-tint text-primary-hover",
  fair: "bg-needs-tint text-needs-text",
  poor: "bg-bad-tint text-bad-text",
};

function ChartCard({ title, lead, children }: { title: string; lead: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-4.5">
      <div className="flex flex-col gap-1">
        <h2 className="text-lead font-bold">{title}</h2>
        <p className="text-caption leading-snug text-ink-2">{lead}</p>
      </div>
      {children}
    </section>
  );
}

/** Each crop's expected harvest this week as a bar, with most years as a thin line through it. */
export function YieldBars({ outlooks }: { outlooks: readonly CropOutlook[] }) {
  return (
    <ChartCard title={en.advice.chartTitle} lead={en.advice.chartLead}>
      <ul className="flex flex-col gap-3">
        {outlooks.map((outlook) => {
          const middle = percent(outlook.rel_yield_p50);
          const low = percent(outlook.rel_yield_p10);
          const high = percent(outlook.rel_yield_p90);
          return (
            <li key={outlook.crop} className="flex flex-col gap-1.5">
              <span className="flex items-baseline justify-between gap-2 text-small">
                <span className="font-bold">{cropLabel(outlook.crop)}</span>
                <span className="font-extrabold">{middle}%</span>
              </span>
              <span aria-hidden="true" className="relative h-4 w-full rounded-pill bg-divider">
                <span
                  className={`absolute inset-y-0 left-0 rounded-pill ${BAR[yieldLevel(outlook.rel_yield_p50)]}`}
                  style={{ width: `${middle}%` }}
                />
                <span
                  className="absolute top-1/2 h-1 -translate-y-1/2 rounded-pill bg-ink"
                  style={{ left: `${low}%`, width: `${Math.max(high - low, 1)}%` }}
                />
              </span>
              <span className="sr-only">{en.advice.range(low, high)}</span>
            </li>
          );
        })}
      </ul>
    </ChartCard>
  );
}

function monthName(month: string): string {
  return en.time.months[Number(month.slice(5, 7)) - 1] ?? month;
}

/** What to sow when: each crop's best expected harvest for a sowing in each month. */
export function MonthTable({ grid }: { grid: MonthGrid }) {
  return (
    <ChartCard title={en.advice.gridTitle} lead={en.advice.gridLead}>
      <table className="w-full table-fixed border-separate border-spacing-1.5 text-small">
        <thead>
          <tr>
            <th scope="col" className="w-[38%]">
              <span className="sr-only">{en.advice.cropColumn}</span>
            </th>
            {grid.months.map((month) => (
              <th key={month} scope="col" className="text-caption font-bold text-ink-2">
                {monthName(month)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.rows.map((row) => (
            <tr key={row.crop}>
              <th scope="row" className="truncate text-left font-bold">
                {cropLabel(row.crop)}
              </th>
              {row.cells.map((cell, index) => {
                const month = grid.months[index] ?? "";
                if (cell === null) return <td key={month} className="text-center text-ink-3">–</td>;
                const level = yieldLevel(cell.yieldP50);
                const value = percent(cell.yieldP50);
                return (
                  <td
                    key={month}
                    aria-label={en.advice.gridCell(
                      cropLabel(row.crop),
                      monthName(month),
                      value,
                      en.advice.levels[level],
                    )}
                    className={`h-12 rounded-chip text-center font-extrabold ${CELL[level]}`}
                  >
                    {value}%
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </ChartCard>
  );
}
