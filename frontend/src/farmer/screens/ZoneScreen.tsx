import { BackHeader } from "../components/BackHeader";
import { Chip } from "../components/Chip";
import { Icon } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { InfoRow } from "../components/InfoRow";
import { MoistureBar } from "../components/MoistureBar";
import { MoistureChart } from "../components/MoistureChart";
import { MoistureDrop } from "../components/MoistureDrop";
import { ScreenBody } from "../components/ScreenBody";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { ZoneView } from "../view-models/types";

export function ZoneScreen({ view }: { view: ZoneView }) {
  return (
    <>
      <BackHeader href={hrefOf({ screen: "today" })} label={en.back.today}>
        <div className="flex flex-1 flex-col">
          <h1 className="text-title-sm font-extrabold tracking-title">{view.name}</h1>
          <span className="text-caption text-ink-3">{view.caption}</span>
        </div>
        <Chip tone={view.tone}>{view.status}</Chip>
      </BackHeader>
      <ScreenBody underHeader>
        <section className="flex flex-col gap-3.5 rounded-card bg-surface p-5">
          <div className="flex items-center gap-3.5">
            <IconCircle tone={view.tone} size="tall">
              <MoistureDrop {...view.soil} size={50} strokeWidth={1.4} />
            </IconCircle>
            <div className="flex flex-col">
              <span className="text-caption font-semibold text-ink-3">{en.zone.waterInSoil}</span>
              <span className="text-hero leading-tight font-extrabold">{view.display}</span>
            </div>
          </div>
          <MoistureBar {...view.soil} />
          <span className="text-small leading-normal text-ink-2">{view.needsMore}</span>
        </section>
        <section className="flex flex-col gap-2.5 rounded-card bg-surface p-4.5">
          <h2 className="text-body font-extrabold">{en.zone.lastDays}</h2>
          <MoistureChart
            values={view.history}
            fieldCapacity={view.soil.fieldCapacity}
            startLabel={view.historyStart}
            alt={view.historyAlt}
          />
        </section>
        <section className="rounded-card bg-surface px-4.5 py-1">
          <InfoRow
            icon={<Icon name="valve" size={26} className="text-ink-2" />}
            value={<span className="text-small font-extrabold">{view.valve}</span>}
          >
            {en.zone.valve}
          </InfoRow>
          <InfoRow
            icon={<Icon name="sensor" size={26} className="text-ink-2" />}
            value={<span className="text-small font-extrabold text-primary">{view.sensor}</span>}
          >
            {en.zone.sensor}
          </InfoRow>
        </section>
      </ScreenBody>
    </>
  );
}
