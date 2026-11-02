import type { ReactNode } from "react";
import { BackHeader } from "../components/BackHeader";
import { Icon, type IconName } from "../components/Icon";
import { IconCircle, type CircleTone } from "../components/IconCircle";
import { MoistureDrop } from "../components/MoistureDrop";
import { ScreenBody } from "../components/ScreenBody";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { ReportRow, ReportRowKind, ReportView, SoilReading } from "../view-models/types";

const ROW_LOOK: Record<Exclude<ReportRowKind, "soil">, { icon: IconName; tone: CircleTone }> = {
  rain: { icon: "cloudRain", tone: "undo" },
  no_rain: { icon: "cloudOff", tone: "undo" },
  done: { icon: "check", tone: "good" },
  waiting: { icon: "clock", tone: "needs" },
  planned: { icon: "calendar", tone: "undo" },
  satellite: { icon: "satellite", tone: "needs" },
};

function rowVisual(kind: ReportRowKind, soil: SoilReading): ReactNode {
  if (kind === "soil") {
    return (
      <IconCircle tone="needs" size="row">
        <MoistureDrop {...soil} size={30} />
      </IconCircle>
    );
  }
  const { icon, tone } = ROW_LOOK[kind];
  return (
    <IconCircle tone={tone} size="row">
      <Icon name={icon} strokeWidth={2} />
    </IconCircle>
  );
}

function Row({ row, soil }: { row: ReportRow; soil: SoilReading }) {
  return (
    <div className="flex items-center gap-3.5 border-b border-divider py-3.5 last:border-b-0">
      {rowVisual(row.kind, soil)}
      <span className="flex-1 text-body leading-snug font-bold">{row.text}</span>
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
      <BackHeader href={hrefOf({ screen: "updates" })} label={en.back.updates}>
        <div className="flex flex-col">
          <h1 className="text-title-sm font-extrabold tracking-title">{view.title}</h1>
          <span className="text-caption text-ink-3">{view.dateLine}</span>
        </div>
      </BackHeader>
      <ScreenBody underHeader>
        <section className="rounded-card bg-surface px-4.5 py-1">
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
