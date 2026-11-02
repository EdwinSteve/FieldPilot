import { en } from "../i18n/en";
import type { UpdateItem, UpdateKind } from "../view-models/types";
import { Icon, type IconName } from "./Icon";
import { IconCircle, type CircleTone } from "./IconCircle";

const LOOK: Record<UpdateKind, { icon: IconName; tone: CircleTone }> = {
  water: { icon: "drop", tone: "good" },
  satellite: { icon: "satellite", tone: "good" },
  report: { icon: "document", tone: "undo" },
  said_no: { icon: "close", tone: "neutral" },
};

export function UpdateRow({ item }: { item: UpdateItem }) {
  const { icon, tone } = LOOK[item.kind];
  return (
    <a
      href={item.href}
      className="flex min-h-14 items-center gap-3.5 border-b border-divider py-3.5 no-underline last:border-b-0"
    >
      <IconCircle tone={tone} size="medium">
        <Icon name={icon} strokeWidth={2} />
      </IconCircle>
      <span className="flex flex-1 flex-col gap-0.5">
        <span className="text-body font-bold text-ink">{item.title}</span>
        <span className="text-caption text-ink-3">{item.time}</span>
      </span>
      {item.unread ? (
        <span className="size-3 shrink-0 rounded-full bg-needs">
          <span className="sr-only">{en.updates.unread}</span>
        </span>
      ) : null}
    </a>
  );
}
