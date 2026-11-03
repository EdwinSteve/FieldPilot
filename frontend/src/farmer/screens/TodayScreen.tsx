import { useState } from "react";
import { BigButton } from "../components/BigButton";
import { Chip } from "../components/Chip";
import { Icon, PlantIcon, StopSign } from "../components/Icon";
import { LEVEL_CHIP, LEVEL_ICON } from "../components/levelStyle";
import { MoistureDrop } from "../components/MoistureDrop";
import { NeedsYouCard } from "../components/NeedsYouCard";
import { RainLevelIcon } from "../components/RainLevelIcon";
import { RecentUpdates } from "../components/RecentUpdates";
import { Sheet } from "../components/Sheet";
import { StatusTile } from "../components/StatusTile";
import { WeekStrip } from "../components/WeekStrip";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { TodayView } from "../view-models/types";

function Header({ view, age }: { view: TodayView; age: string | null }) {
  return (
    <header className="flex items-start justify-between gap-3 px-0.5">
      <div className="flex flex-col gap-0.5">
        <span className="text-small text-ink-3">{view.dateLine}</span>
        <h1 className="text-title font-extrabold tracking-title">{view.greeting}</h1>
        <span className="text-caption text-ink-3">{view.farmLine}</span>
        {age === null ? null : (
          <span className="text-caption text-ink-3">{en.freshness.updated(age)}</span>
        )}
      </div>
      <a
        href={hrefOf({ screen: "stop" })}
        className="press flex min-h-16 min-w-16 shrink-0 flex-col items-center justify-center gap-0.5 rounded-control border-2 border-stop bg-surface text-caption font-extrabold text-stop no-underline"
      >
        <StopSign size={24} />
        {en.today.stop}
      </a>
    </header>
  );
}

function StoppedBanner({ text }: { text: string }) {
  return (
    <a
      href={hrefOf({ screen: "stop" })}
      className="press flex animate-card-in items-center gap-3.5 rounded-card bg-stop p-4.5 text-surface no-underline"
    >
      <StopSign size={36} inverted />
      <span className="flex flex-col gap-0.5">
        <span className="text-key font-extrabold">{text}</span>
        <span className="text-small">{en.today.stoppedDetail}</span>
      </span>
    </a>
  );
}

function StatusCard({ view }: { view: TodayView }) {
  const zoneHref = hrefOf({ screen: "zone", zoneId: view.zoneId });
  const statusIcon = LEVEL_ICON[view.status];
  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-4">
      <span className="self-start">
        <Chip tone={LEVEL_CHIP[view.status]}>
          {statusIcon === null ? null : <Icon name={statusIcon} size={16} strokeWidth={2.6} />}
          {view.statusLabel}
        </Chip>
      </span>
      <a
        href={zoneHref}
        className="flex items-center justify-between gap-2.5 px-0.5 text-ink no-underline"
      >
        <span className="flex flex-col gap-0.5">
          <h2 className="text-key-lg font-extrabold tracking-key">{view.statusTitle}</h2>
          <span className="text-small text-ink-2">{view.statusDetail}</span>
        </span>
        <Icon name="forward" size={22} strokeWidth={2.5} className="text-ink-3" />
      </a>
      <div className="grid grid-cols-3 gap-2">
        <StatusTile
          href={zoneHref}
          level={view.soil.level}
          visual={<MoistureDrop {...view.soil} size={40} />}
          value={view.soil.display}
          valueNote={view.soil.ofFull}
          trend={view.soil.trend}
          label={view.soil.label}
        />
        <StatusTile
          href={zoneHref}
          level="info"
          visual={
            view.rain.known ? (
              <RainLevelIcon mm={view.rain.mm} size={40} />
            ) : (
              <Icon name="cloud" size={40} strokeWidth={1.8} className="text-undo-icon" />
            )
          }
          value={view.rain.display}
          label={view.rain.label}
        />
        <StatusTile
          href={hrefOf({ screen: "field" })}
          level={view.plants.level}
          visual={<PlantIcon size={40} />}
          value={view.plants.value}
          label={view.plants.label}
        />
      </div>
    </section>
  );
}

function Word({ term, children }: { term: React.ReactNode; children: string }) {
  return (
    <div className="flex flex-col items-start gap-1.5 border-b border-divider pb-3 last:border-b-0 last:pb-0">
      {term}
      <p className="text-body leading-snug text-ink-2">{children}</p>
    </div>
  );
}

/** Plain meanings of the few words and numbers the app leans on. */
function WordsSheet({ view, onClose }: { view: TodayView; onClose: () => void }) {
  const { display, fieldCapacity } = view.soil;
  return (
    <Sheet label={en.words.title} onClose={onClose}>
      <h2 className="text-head font-extrabold">{en.words.title}</h2>
      <div className="flex max-h-[60dvh] flex-col gap-3 overflow-y-auto">
        <Word term={<Chip tone="needs">{en.autonomy.needsYou}</Chip>}>{en.words.needsYou}</Word>
        <Word term={<Chip tone="good">{en.autonomy.automatic}</Chip>}>{en.words.automatic}</Word>
        <Word term={<Chip tone="undo">{en.autonomy.canUndo}</Chip>}>{en.words.canUndo}</Word>
        <Word
          term={
            <span className="text-lead font-extrabold">
              {view.soil.ofFull === null ? en.soil.tileUnknown : `${display} ${view.soil.ofFull}`}
            </span>
          }
        >
          {view.soil.ofFull === null
            ? en.words.soilUnknown(fieldCapacity)
            : en.words.soil(display, fieldCapacity)}
        </Word>
        <Word
          term={
            <span className="inline-flex items-center gap-1.5 text-lead font-extrabold text-stop">
              <StopSign size={22} />
              {en.today.stop}
            </span>
          }
        >
          {en.words.stop}
        </Word>
      </div>
      <BigButton variant="outline" onClick={onClose}>
        {en.words.close}
      </BigButton>
    </Sheet>
  );
}

interface TodayScreenProps {
  view: TodayView;
  /** How old the farm on screen is; null when unknown. */
  age: string | null;
}

export function TodayScreen({ view, age }: TodayScreenProps) {
  const [wordsOpen, setWordsOpen] = useState(false);
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pt-6 pb-4.5">
      <Header view={view} age={age} />
      {view.stoppedBanner === null ? null : <StoppedBanner text={view.stoppedBanner} />}
      {view.decision ? <NeedsYouCard decision={view.decision} /> : null}
      <StatusCard view={view} />
      <WeekStrip week={view.week} />
      <RecentUpdates items={view.recent} />
      <button
        type="button"
        onClick={() => setWordsOpen(true)}
        className="press inline-flex min-h-12 items-center justify-center gap-2 self-center border-0 bg-transparent px-3 text-small font-bold text-primary"
      >
        <Icon name="info" size={20} />
        {en.today.wordsLink}
      </button>
      {wordsOpen ? <WordsSheet view={view} onClose={() => setWordsOpen(false)} /> : null}
    </main>
  );
}
