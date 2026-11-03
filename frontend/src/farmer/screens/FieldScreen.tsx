import { BackHeader } from "../components/BackHeader";
import { BigLink } from "../components/BigButton";
import { FieldPhoto } from "../components/FieldPhoto";
import { Icon, PlantIcon } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { ScreenBody } from "../components/ScreenBody";
import { StateView } from "../components/StateView";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { FieldView } from "../view-models/types";

export function FieldScreen({ view }: { view: FieldView | null }) {
  if (view === null) {
    return <StateView icon="satellite" title={en.field.emptyTitle} detail={en.field.emptyDetail} />;
  }
  return (
    <>
      <BackHeader>
        <div className="flex flex-col">
          <h1 className="text-head font-extrabold tracking-title">{en.field.title}</h1>
          <span className="text-caption text-ink-3">{view.caption}</span>
        </div>
      </BackHeader>
      <ScreenBody underHeader>
        <section className="flex items-center gap-3.5 rounded-card bg-surface p-4.5">
          <IconCircle tone="needs" size="wide">
            <PlantIcon size={40} />
          </IconCircle>
          <span className="flex flex-col gap-1">
            <span className="text-key-lg font-extrabold tracking-key">{view.headline}</span>
            <span className="text-body leading-snug text-ink-2">
              {view.detail}
              {view.barePct === null ? null : (
                <>
                  {en.field.bareBefore}
                  <strong className="text-needs-text">{view.barePct}</strong>
                  {en.field.bareAfter}
                </>
              )}
            </span>
          </span>
        </section>
        <FieldPhoto
          imageUrl={view.imageUrl}
          alt={view.imageAlt}
          zoneLabel={view.zoneLabel}
          zoneArea={view.zoneArea}
          spots={view.spots}
        />
        <BigLink variant="primary" size="compact" href={hrefOf({ screen: "talk" })}>
          <Icon name="mic" />
          {en.field.askAboutThis}
        </BigLink>
      </ScreenBody>
    </>
  );
}
