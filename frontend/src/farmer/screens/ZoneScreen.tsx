import { BackHeader } from "../components/BackHeader";
import { Chip } from "../components/Chip";
import { Icon } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { InfoRow } from "../components/InfoRow";
import { LEVEL_CHIP, LEVEL_CIRCLE, LEVEL_TEXT } from "../components/levelStyle";
import { MoistureBar } from "../components/MoistureBar";
import { MoistureChart } from "../components/MoistureChart";
import { MoistureDrop } from "../components/MoistureDrop";
import { ScreenBody } from "../components/ScreenBody";
import { en } from "../i18n/en";
import type { ZoneView } from "../view-models/types";

export function ZoneScreen({ view }: { view: ZoneView }) {
  return (
    <>
      <BackHeader>
        <div className="flex flex-1 flex-col">
          <h1 className="text-title-sm font-extrabold tracking-title">{view.name}</h1>
          <span className="text-caption text-ink-3">{view.caption}</span>
        </div>
        <Chip tone={LEVEL_CHIP[view.level]}>{view.status}</Chip>
      </BackHeader>
      <ScreenBody underHeader>
        {view.asOf === null ? null : (
          <div className="flex shrink-0 items-center gap-3 rounded-tile bg-undo-tint py-2 pr-2 pl-4 text-undo-text">
            <Icon name="calendar" size={22} strokeWidth={2.2} className="shrink-0" />
            <span className="flex-1 text-small font-extrabold leading-snug">{view.asOf.label}</span>
            <a
              href={view.asOf.nowHref}
              className="press flex min-h-12 shrink-0 items-center gap-1 rounded-control bg-surface px-3.5 text-small font-extrabold text-undo-text no-underline"
            >
              {en.zone.seeNow}
              <Icon name="forward" size={18} strokeWidth={2.6} />
            </a>
          </div>
        )}
        <section className="flex flex-col gap-3.5 rounded-card bg-surface p-5">
          <div className="flex items-center gap-3.5">
            <IconCircle tone={LEVEL_CIRCLE[view.level]} size="tall">
              <MoistureDrop {...view.soil} size={50} strokeWidth={1.4} />
            </IconCircle>
            <div className="flex flex-col">
              <span className="text-caption font-semibold text-ink-3">{en.zone.waterInSoil}</span>
              <span className="text-hero leading-tight font-extrabold">{view.display}</span>
              {view.percentFull === null ? null : (
                <span className="text-small font-bold text-ink-2">{view.percentFull}</span>
              )}
            </div>
          </div>
          <MoistureBar {...view.soil} />
          <span className="text-small leading-normal text-ink-2">{view.needsMore}</span>
          {view.trend === null ? null : (
            <span className="text-small leading-normal text-ink-2">{view.trend}</span>
          )}
        </section>
        <section className="flex flex-col gap-2.5 rounded-card bg-surface p-4.5">
          <h2 className="text-body font-extrabold">{en.zone.lastDays}</h2>
          <MoistureChart
            values={view.history}
            fieldCapacity={view.soil.fieldCapacity}
            startLabel={view.historyStart}
            alt={view.historyAlt}
            level={view.level}
          />
        </section>
        {/* The valve and the sensor say how things are now: not shown for a past moment. */}
        {view.asOf !== null ? null : (
          <section className="rounded-card bg-surface px-4.5 py-1">
            <InfoRow
              icon={<Icon name="valve" size={26} className="text-ink-2" />}
              value={
                <span className={`text-small font-extrabold ${LEVEL_TEXT[view.valveLevel]}`}>
                  {view.valve}
                </span>
              }
            >
              {en.zone.valve}
            </InfoRow>
            <InfoRow
              icon={<Icon name="sensor" size={26} className="text-ink-2" />}
              value={
                <span className={`text-small font-extrabold ${LEVEL_TEXT[view.sensorLevel]}`}>
                  {view.sensor}
                </span>
              }
            >
              {en.zone.sensor}
            </InfoRow>
          </section>
        )}
      </ScreenBody>
    </>
  );
}
