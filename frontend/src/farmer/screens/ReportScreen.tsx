import { useId, useState, type ReactNode } from "react";
import { BackHeader } from "../components/BackHeader";
import { BigLink } from "../components/BigButton";
import { Icon, type IconName } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { levelFill } from "../components/levelStyle";
import { MoistureDrop } from "../components/MoistureDrop";
import { ScreenBody } from "../components/ScreenBody";
import { en } from "../i18n/en";
import type { ReportItem, ReportTile, ReportView, SoilReading } from "../view-models/types";

/*
 * Three groups that read as a story, each with its own look: what FieldPilot saw as small
 * reading tiles, what it did as the one solid green card, what comes next as cards with an
 * edge and a button. The icon and the words carry each meaning; the colour only repeats it.
 */

function GroupTitle({ children }: { children: string }) {
  return (
    <h2 className="mt-1 px-0.5 text-caption font-extrabold tracking-wide text-ink-3 uppercase">
      {children}
    </h2>
  );
}

function TileBody({ tile, soil }: { tile: ReportTile; soil: SoilReading }) {
  return (
    <>
      {tile.kind === "soil" ? (
        <MoistureDrop {...soil} size={36} />
      ) : (
        <Icon
          name={tile.label === en.report.noRainToday ? "cloudOff" : "cloudRain"}
          size={34}
          strokeWidth={1.9}
        />
      )}
      <span className="flex flex-wrap items-baseline gap-x-1">
        <span className="text-key-lg font-extrabold">{tile.value}</span>
        {tile.note === null ? null : <span className="text-caption font-bold">{tile.note}</span>}
      </span>
      <span className="text-small leading-snug font-bold">{tile.label}</span>
    </>
  );
}

function Tile({ tile, soil }: { tile: ReportTile; soil: SoilReading }) {
  const look = `relative flex flex-col items-start gap-1.5 rounded-tile p-3.5 no-underline ${levelFill(tile.level)}`;
  if (tile.href === null) {
    return (
      <div className={look}>
        <TileBody tile={tile} soil={soil} />
      </div>
    );
  }
  return (
    <a href={tile.href} className={`press ${look}`}>
      <Icon name="forward" size={18} strokeWidth={2.6} className="absolute top-3 right-3" />
      <TileBody tile={tile} soil={soil} />
    </a>
  );
}

function SeenCard({ item }: { item: ReportItem }) {
  const body = (
    <>
      <IconCircle tone="needs" size="small">
        <Icon name="satellite" size={22} strokeWidth={2.2} />
      </IconCircle>
      <span className="flex flex-1 flex-col gap-0.5">
        <span className="text-body font-extrabold text-ink">{item.title}</span>
        <span className="text-small leading-snug text-ink-2">{item.detail}</span>
      </span>
      {item.href === null ? null : (
        <Icon name="forward" size={22} strokeWidth={2.5} className="shrink-0 text-ink-3" />
      )}
    </>
  );
  const look = "flex min-h-16 items-center gap-3 rounded-tile bg-surface px-3.5 py-3 no-underline";
  return item.href === null ? (
    <div className={look}>{body}</div>
  ) : (
    <a href={item.href} className={`press ${look}`}>
      {body}
    </a>
  );
}

function DoneCard({ item }: { item: ReportItem }) {
  return (
    <div className="relative isolate flex items-start gap-3 overflow-hidden rounded-card bg-primary p-4 text-surface">
      <span
        aria-hidden="true"
        className="absolute -top-10 -right-10 -z-10 size-32 rounded-full bg-field opacity-60"
      />
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface text-primary">
        <Icon name="check" size={24} strokeWidth={3} />
      </span>
      <span className="flex flex-col gap-1">
        <span className="text-key font-extrabold">{item.title}</span>
        <span className="text-body leading-snug">{item.detail}</span>
      </span>
    </div>
  );
}

const NEXT_LOOK: Record<"planned" | "waiting", { icon: IconName; edge: string; tone: "undo" | "needs" }> = {
  planned: { icon: "calendar", edge: "border-undo", tone: "undo" },
  waiting: { icon: "clock", edge: "border-needs", tone: "needs" },
};

function NextCard({ item }: { item: ReportItem }) {
  const look = NEXT_LOOK[item.kind === "waiting" ? "waiting" : "planned"];
  return (
    <div className={`flex flex-col gap-3 rounded-tile border-l-[6px] bg-surface p-4 ${look.edge}`}>
      <div className="flex items-start gap-3">
        <IconCircle tone={look.tone} size="small">
          <Icon name={look.icon} size={22} strokeWidth={2.2} />
        </IconCircle>
        <span className="flex flex-col gap-1">
          <span className="text-body font-extrabold text-ink">{item.title}</span>
          <span className="text-small leading-snug text-ink-2">{item.detail}</span>
        </span>
      </div>
      {item.href === null || item.action === null ? null : (
        <BigLink variant={look.tone} size="compact" href={item.href}>
          {item.action}
          <Icon name="forward" size={22} strokeWidth={2.6} />
        </BigLink>
      )}
    </div>
  );
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex shrink-0 flex-col gap-2">
      <GroupTitle>{title}</GroupTitle>
      {children}
    </section>
  );
}

/** The report as FieldPilot wrote it, closed until asked for: the groups above already say it. */
function FullReport({ text, language }: { text: string; language: string | null }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <section className="flex shrink-0 flex-col rounded-control bg-surface">
      <h2 className="m-0">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((current) => !current)}
          className="press flex min-h-16 w-full items-center justify-between gap-3 rounded-control border-0 bg-transparent px-4 text-left text-body font-bold text-ink"
        >
          {language === null ? en.report.full : en.report.fullIn(language)}
          <Icon
            name="chevronDown"
            size={22}
            strokeWidth={2.5}
            className={`shrink-0 text-ink-3 transition-transform duration-300 ease-(--ease-calm) ${open ? "rotate-180" : ""}`}
          />
        </button>
      </h2>
      <div
        id={id}
        inert={!open}
        className={`grid transition-[grid-template-rows,opacity,visibility] duration-300 ease-(--ease-calm) ${
          open ? "grid-rows-[1fr] opacity-100" : "invisible grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="flex flex-col gap-3 px-4 pb-4">
            <p lang={language === null ? undefined : "es"} className="text-body leading-relaxed text-ink-2">
              {text}
            </p>
            <div className="flex items-center gap-3 rounded-control bg-tint px-4 py-3.5">
              <Icon name="shield" size={28} strokeWidth={2.1} className="shrink-0 text-primary" />
              <span className="text-small leading-snug font-bold text-primary-hover">
                {en.report.verified}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
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
        {view.tiles.length + view.seen.length === 0 ? null : (
          <Group title={en.report.seenTitle}>
            {view.tiles.length === 0 ? null : (
              <div className="grid grid-cols-2 gap-2">
                {view.tiles.map((tile) => (
                  <Tile key={tile.kind} tile={tile} soil={view.soil} />
                ))}
              </div>
            )}
            {view.seen.map((item) => (
              <SeenCard key={item.title} item={item} />
            ))}
          </Group>
        )}
        {view.done.length === 0 ? null : (
          <Group title={en.report.doneTitle}>
            {view.done.map((item) => (
              <DoneCard key={item.title} item={item} />
            ))}
          </Group>
        )}
        {view.next.length === 0 ? null : (
          <Group title={en.report.nextTitle}>
            {view.next.map((item) => (
              <NextCard key={item.title} item={item} />
            ))}
          </Group>
        )}
        <FullReport text={view.full} language={view.fullLanguage} />
        {view.saidNo ? (
          <div className="flex shrink-0 items-center gap-3 rounded-control bg-surface px-4 py-3.5">
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
            className="press flex min-h-15 shrink-0 items-center justify-between rounded-control border-2 border-border bg-surface px-4.5 text-body font-bold text-ink no-underline"
          >
            {view.other.label}
            <Icon name="forward" size={22} strokeWidth={2.5} className="text-ink-3" />
          </a>
        ) : null}
      </ScreenBody>
    </>
  );
}
