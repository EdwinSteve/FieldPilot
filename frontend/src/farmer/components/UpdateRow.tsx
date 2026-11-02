import { en } from "../i18n/en";
import type { Level } from "../lib/statusLevel";
import type { UpdateItem, UpdateKind } from "../view-models/types";
import { Icon, type IconName } from "./Icon";
import { CardIcon } from "./IconCircle";
import { levelCard } from "./levelStyle";

const LOOK: Record<UpdateKind, { icon: IconName; level: Level }> = {
  water: { icon: "drop", level: "good" },
  undo: { icon: "drop", level: "info" },
  satellite: { icon: "satellite", level: "watch" },
  report: { icon: "document", level: "neutral" },
  said_no: { icon: "close", level: "neutral" },
  problem: { icon: "warning", level: "bad" },
  alert: { icon: "warning", level: "bad" },
};

export function UpdateRow({ item }: { item: UpdateItem }) {
  const { icon, level } = LOOK[item.kind];
  const row = `flex min-h-14 items-center gap-3.5 no-underline ${levelCard(level)}`;
  const content = (
    <>
      <CardIcon level={level}>
        <Icon name={icon} strokeWidth={2} />
      </CardIcon>
      <span className="flex flex-1 flex-col gap-0.5">
        <span lang={item.lang} className="text-body font-bold text-ink">
          {item.title}
        </span>
        <span className="text-caption text-ink-2">{item.time}</span>
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
