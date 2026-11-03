import { useState } from "react";
import appIcon from "../assets/icon-180.png";
import { BigButton } from "../components/BigButton";
import { Chip } from "../components/Chip";
import { HarvestSheet, type HarvestNote } from "../components/HarvestSheet";
import { Icon, PlantIcon, StopSign } from "../components/Icon";
import { LEVEL_CHIP, LEVEL_ICON } from "../components/levelStyle";
import { MoistureDrop } from "../components/MoistureDrop";
import { NeedsYouCard } from "../components/NeedsYouCard";
import { RainLevelIcon } from "../components/RainLevelIcon";
import { RecentUpdates } from "../components/RecentUpdates";
import { SalesCard } from "../components/SalesCard";
import { SettingsLink } from "../components/SettingsLink";
import { Sheet } from "../components/Sheet";
import { StatusTile } from "../components/StatusTile";
import { WeekStrip } from "../components/WeekStrip";
import { Wordmark } from "../components/Wordmark";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { PlantedNote, TodayHarvest, TodayView } from "../view-models/types";

/** The app's own bar: whose app this is on the left, the two ways out of the day on the right. */
function TopBar() {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex min-w-0 items-center gap-2.5">
        <img src={appIcon} alt="" width={40} height={40} className="size-10 shrink-0 rounded-tile" />
        <Wordmark />
      </span>
      <div className="flex shrink-0 items-center gap-2">
        <a
          href={hrefOf({ screen: "stop" })}
          className="press flex min-h-16 min-w-16 shrink-0 flex-col items-center justify-center gap-0.5 rounded-control border-2 border-stop bg-surface text-caption font-extrabold text-stop no-underline"
        >
          <StopSign size={24} />
          {en.today.stop}
        </a>
        <SettingsLink />
      </div>
    </div>
  );
}

function Header({ view, age }: { view: TodayView; age: string | null }) {
  return (
    <header className="flex flex-col gap-4 px-0.5">
      <TopBar />
      {/* The day, the greeting and the farm read as one group, at the full width. */}
      <div className="flex flex-col gap-0.5">
        <span className="text-small text-ink-3">{view.dateLine}</span>
        <h1 className="text-title font-extrabold tracking-title">{view.greeting}</h1>
        <span className="text-caption text-ink-3">{view.farmLine}</span>
        {age === null ? null : (
          <span className="text-caption text-ink-3">{en.freshness.updated(age)}</span>
        )}
      </div>
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

/** Right after sowing: what FieldPilot does from now on, so the farmer knows it worked. */
function PlantedCard({ note, onOk }: { note: PlantedNote; onOk: () => void }) {
  return (
    <output className="flex animate-card-in flex-col gap-3 rounded-card bg-tint p-4.5">
      <div className="flex gap-3">
        <span className="mt-0.5 shrink-0">
          <PlantIcon size={30} />
        </span>
        <div className="flex flex-col gap-1">
          <h2 className="text-lead font-extrabold text-primary-hover">{en.planted.title(note.crop)}</h2>
          <p className="text-body leading-snug">{note.automated ? en.planted.automated : en.planted.manual}</p>
        </div>
      </div>
      <BigButton variant="outline" size="compact" onClick={onOk}>
        {en.planted.ok}
      </BigButton>
    </output>
  );
}

/** A decision answered without signal: no question to ask again, only that it waits. */
function SavedAnswerCard() {
  return (
    <output className="flex animate-card-in gap-3 rounded-card bg-undo-tint p-4.5 text-undo-text">
      <Icon name="cloudOff" size={28} className="mt-0.5 shrink-0" />
      <div className="flex flex-col gap-1">
        <h2 className="text-lead font-extrabold">{en.outbox.waitingTitle}</h2>
        <p className="text-body leading-snug">{en.outbox.waitingDetail}</p>
      </div>
    </output>
  );
}

/** Near harvest time a card with the form one tap away; for a manual crop, a quiet row. */
function HarvestCard({ harvest, onOpen }: { harvest: TodayHarvest; onOpen: () => void }) {
  if (harvest.kind === "record") {
    return (
      <button
        type="button"
        onClick={onOpen}
        className="press flex min-h-16 items-center gap-3 rounded-card border-0 bg-surface px-4.5 py-3 text-left"
      >
        <PlantIcon size={28} />
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-body font-extrabold">{harvest.title}</span>
          <span className="text-small text-ink-2">{harvest.detail}</span>
        </span>
        <Icon name="forward" size={22} className="shrink-0 text-ink-3" />
      </button>
    );
  }
  const ready = harvest.kind === "ready";
  return (
    <section className={`flex animate-card-in flex-col gap-3 rounded-card p-4.5 ${ready ? "bg-tint" : "bg-surface"}`}>
      <div className="flex gap-3">
        <span className="mt-0.5 shrink-0">
          <PlantIcon size={30} />
        </span>
        <div className="flex flex-col gap-1">
          <h2 className="text-lead font-extrabold">{harvest.title}</h2>
          <p className="text-body leading-snug text-ink-2">{harvest.detail}</p>
        </div>
      </div>
      <BigButton variant={ready ? "primary" : "outline"} size="compact" onClick={onOpen}>
        {en.harvest.open}
      </BigButton>
    </section>
  );
}

interface TodayScreenProps {
  view: TodayView;
  /** How old the farm on screen is; null when unknown. */
  age: string | null;
  /** Just planted: said once, until the farmer taps OK. */
  planted: PlantedNote | null;
  onPlantedSeen: () => void;
  /** Decisions answered without signal, waiting to be sent. */
  savedAnswers: readonly number[];
  onHarvested: (note: HarvestNote) => void;
  plotId: number;
}

export function TodayScreen({ view, age, planted, onPlantedSeen, savedAnswers, onHarvested, plotId }: TodayScreenProps) {
  const [wordsOpen, setWordsOpen] = useState(false);
  const [harvesting, setHarvesting] = useState(false);
  const harvest = view.harvest;
  const decisionSaved = view.decision !== null && savedAnswers.includes(view.decision.taskId);
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pt-4 pb-4.5">
      <Header view={view} age={age} />
      {view.stoppedBanner === null ? null : <StoppedBanner text={view.stoppedBanner} />}
      {planted === null ? null : <PlantedCard note={planted} onOk={onPlantedSeen} />}
      {view.decision === null ? null : decisionSaved ? <SavedAnswerCard /> : <NeedsYouCard decision={view.decision} />}
      {harvest !== null && harvest.kind !== "record" ? (
        <HarvestCard harvest={harvest} onOpen={() => setHarvesting(true)} />
      ) : null}
      <StatusCard view={view} />
      <WeekStrip week={view.week} />
      {harvest?.kind === "record" ? <HarvestCard harvest={harvest} onOpen={() => setHarvesting(true)} /> : null}
      <SalesCard plotId={plotId} />
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
      {harvesting && harvest !== null ? (
        <HarvestSheet info={harvest.info} onClose={() => setHarvesting(false)} onSaved={onHarvested} />
      ) : null}
    </main>
  );
}
