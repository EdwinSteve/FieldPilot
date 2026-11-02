import { Icon, PlantIcon, StopSign } from "../components/Icon";
import { MoistureDrop } from "../components/MoistureDrop";
import { NeedsYouCard } from "../components/NeedsYouCard";
import { RainLevelIcon } from "../components/RainLevelIcon";
import { StatusTile } from "../components/StatusTile";
import { WeekStrip } from "../components/WeekStrip";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { TodayView } from "../view-models/types";

function Header({ view }: { view: TodayView }) {
  return (
    <header className="flex items-start justify-between gap-3 px-0.5">
      <div className="flex flex-col gap-0.5">
        <span className="text-small text-ink-3">{view.dateLine}</span>
        <h1 className="text-title font-extrabold tracking-title">{view.greeting}</h1>
        <span className="text-caption text-ink-3">{view.farmLine}</span>
      </div>
      <a
        href={hrefOf({ screen: "stop" })}
        className="flex min-h-16 min-w-16 shrink-0 flex-col items-center justify-center gap-0.5 rounded-control border-2 border-stop bg-surface text-caption font-extrabold text-stop no-underline"
      >
        <StopSign size={24} />
        {en.today.stop}
      </a>
    </header>
  );
}

function StoppedBanner() {
  return (
    <a
      href={hrefOf({ screen: "stop" })}
      className="flex items-center gap-3.5 rounded-card bg-stop p-4.5 text-surface no-underline"
    >
      <StopSign size={36} inverted />
      <span className="flex flex-col gap-0.5">
        <span className="text-key font-extrabold">{en.today.stoppedBanner}</span>
        <span className="text-small">{en.today.stoppedDetail}</span>
      </span>
    </a>
  );
}

function StatusCard({ view }: { view: TodayView }) {
  const zoneHref = hrefOf({ screen: "zone", zoneId: view.zoneId });
  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-4">
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
          tone="needs"
          visual={<MoistureDrop {...view.soil} size={40} />}
          value={`${view.soil.value}%`}
          label={view.soil.label}
        />
        <StatusTile
          href={zoneHref}
          tone="rain"
          visual={<RainLevelIcon mm={view.rain.mm} size={40} />}
          value={`${view.rain.mm} mm`}
          label={view.rain.label}
        />
        <StatusTile
          href={hrefOf({ screen: "field" })}
          tone="good"
          visual={<PlantIcon size={40} />}
          value={view.plants.value}
          label={view.plants.label}
        />
      </div>
    </section>
  );
}

export function TodayScreen({ view }: { view: TodayView }) {
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pt-6 pb-4.5">
      <Header view={view} />
      {view.stopped ? <StoppedBanner /> : null}
      {view.decision ? <NeedsYouCard decision={view.decision} /> : null}
      <StatusCard view={view} />
      <WeekStrip week={view.week} />
    </main>
  );
}
