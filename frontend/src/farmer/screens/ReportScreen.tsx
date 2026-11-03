import { BackHeader } from "../components/BackHeader";
import { Icon, type IconName } from "../components/Icon";
import { CardIcon, IconCircle } from "../components/IconCircle";
import { levelCard } from "../components/levelStyle";
import { MoistureDrop } from "../components/MoistureDrop";
import { ScreenBody } from "../components/ScreenBody";
import { en } from "../i18n/en";
import { soilStatus } from "../lib/soilStatus";
import { soilLevel, type Level } from "../lib/statusLevel";
import type { ReportRow, ReportRowKind, ReportView, SoilReading } from "../view-models/types";

const ROW_LOOK: Record<Exclude<ReportRowKind, "soil">, { icon: IconName; level: Level }> = {
  rain: { icon: "cloudRain", level: "info" },
  no_rain: { icon: "cloudOff", level: "info" },
  done: { icon: "check", level: "good" },
  waiting: { icon: "clock", level: "watch" },
  planned: { icon: "calendar", level: "info" },
  satellite: { icon: "satellite", level: "watch" },
};

function Row({ row, soil }: { row: ReportRow; soil: SoilReading }) {
  const level =
    row.kind === "soil"
      ? soilLevel(soilStatus(soil.value, soil.fieldCapacity))
      : ROW_LOOK[row.kind].level;
  return (
    <div className={`flex items-center gap-3.5 ${levelCard(level)}`}>
      <CardIcon level={level} size="row">
        {row.kind === "soil" ? (
          <MoistureDrop {...soil} size={30} />
        ) : (
          <Icon name={ROW_LOOK[row.kind].icon} strokeWidth={2} />
        )}
      </CardIcon>
      <span className="flex-1 text-body leading-snug font-bold text-ink">{row.text}</span>
    </div>
  );
}

function OriginalReport({ text }: { text: string }) {
  return (
    <details className="group rounded-control bg-surface px-4">
      <summary className="flex min-h-15 cursor-pointer list-none items-center justify-between gap-3 text-body font-bold">
        {en.report.original}
        <Icon
          name="forward"
          size={22}
          strokeWidth={2.5}
          className="text-ink-3 transition-transform group-open:rotate-90"
        />
      </summary>
      <div className="flex flex-col gap-3 pb-4">
        <p lang="es" className="text-body leading-relaxed text-ink-2">
          {text}
        </p>
        <div className="flex items-center gap-3 rounded-control bg-tint px-4 py-3.5">
          <Icon name="shield" size={28} strokeWidth={2.1} className="shrink-0 text-primary" />
          <span className="text-small leading-snug font-bold text-primary-hover">
            {en.report.verified}
          </span>
        </div>
      </div>
    </details>
  );
}

export function ReportScreen({ view }: { view: ReportView }) {
  return (
    <>
      <BackHeader>
        <div className="flex flex-col">
          <h1 className="text-title-sm font-extrabold tracking-title">{view.title}</h1>
          <span className="text-caption text-ink-3">{view.dateLine}</span>
        </div>
      </BackHeader>
      <ScreenBody underHeader>
        <section className="flex flex-col gap-2">
          {view.rows.map((row) => (
            <Row key={row.text} row={row} soil={view.soil} />
          ))}
        </section>
        <OriginalReport text={view.original} />
        {view.saidNo ? (
          <div className="flex items-center gap-3 rounded-control bg-surface px-4 py-3.5">
            <IconCircle tone="neutral" size="small">
              <Icon name="close" size={22} strokeWidth={2.4} />
            </IconCircle>
            <span className="flex flex-col gap-0.5">
              <span className="text-small font-extrabold">{en.report.saidNo}</span>
              <span className="text-caption text-ink-3">{view.saidNo.detail}</span>
            </span>
          </div>
        ) : null}
        {view.other ? (
          <a
            href={view.other.href}
            className="press flex min-h-15 items-center justify-between rounded-control border-2 border-border bg-surface px-4.5 text-body font-bold text-ink no-underline"
          >
            {view.other.label}
            <Icon name="forward" size={22} strokeWidth={2.5} className="text-ink-3" />
          </a>
        ) : null}
      </ScreenBody>
    </>
  );
}
