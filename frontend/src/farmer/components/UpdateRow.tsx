import { en } from "../i18n/en";
import type { Level } from "../lib/statusLevel";
import type { UpdateItem, UpdateKind } from "../view-models/types";
import { Icon, type IconName } from "./Icon";
import { CardIcon, IconCircle, type CircleTone } from "./IconCircle";
import { levelCard } from "./levelStyle";

/** `tone` colours only the icon, on a white row: water is blue, as on the week strip and the rain tile. */
const LOOK: Record<UpdateKind, { icon: IconName; level: Level; tone?: CircleTone }> = {
  water: { icon: "drop", level: "neutral", tone: "undo" },
  undo: { icon: "undo", level: "info" },
  satellite: { icon: "satellite", level: "watch" },
  report: { icon: "document", level: "neutral" },
  said_no: { icon: "close", level: "neutral" },
  work: { icon: "field", level: "info" },
  problem: { icon: "warning", level: "bad" },
  alert: { icon: "warning", level: "bad" },
};

interface UpdateRowProps {
  item: UpdateItem;
  /** Under a day heading: the time leaves out the day the heading already says. */
  underDay?: boolean;
}

export function UpdateRow({ item, underDay = false }: UpdateRowProps) {
  const { icon, level, tone } = LOOK[item.kind];
  const row = `flex min-h-14 items-center gap-3.5 no-underline ${levelCard(level)}`;
  const content = (
    <>
      {tone === undefined ? (
        <CardIcon level={level}>
          <Icon name={icon} strokeWidth={2} />
        </CardIcon>
      ) : (
        <IconCircle tone={tone} size="medium">
          <Icon name={icon} strokeWidth={2} />
        </IconCircle>
      )}
      <span className="flex flex-1 flex-col gap-0.5">
        <span lang={item.lang} className="text-body font-bold text-ink">
          {item.title}
        </span>
        <span className="text-caption text-ink-2">{underDay ? item.timeInDay : item.time}</span>
      </span>
      {item.unread ? (
        <span className="size-3 shrink-0 rounded-full bg-current">
          <span className="sr-only">{en.updates.unread}</span>
        </span>
      ) : null}
    </>
  );
  if (item.href === null) return <div className={row}>{content}</div>;
  return (
    <a href={item.href} className={`press ${row}`}>
      {content}
    </a>
  );
}
