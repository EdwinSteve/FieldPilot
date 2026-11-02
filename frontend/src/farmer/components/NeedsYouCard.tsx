import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { DecisionLink } from "../view-models/types";
import { Chip } from "./Chip";
import { Icon } from "./Icon";
import { IconCircle } from "./IconCircle";

export function NeedsYouCard({ decision }: { decision: DecisionLink }) {
  return (
    <a
      href={hrefOf({ screen: "decide", taskId: decision.taskId })}
      className="flex flex-col gap-3 rounded-card-lg border-3 border-needs bg-surface p-4.5 text-ink no-underline shadow-needs"
    >
      <span className="self-start">
        <Chip tone="needs">{en.autonomy.needsYou}</Chip>
      </span>
      <span className="flex items-center gap-3.5">
        <IconCircle tone="needsSolid" size="wide">
          <Icon name="drop" size={32} />
        </IconCircle>
        <span className="flex flex-1 flex-col gap-0.5">
          <span className="text-head font-extrabold tracking-key">{decision.question}</span>
          <span className="text-body text-ink-2">{en.today.tapToAnswer}</span>
        </span>
        <Icon name="forward" size={26} strokeWidth={2.6} className="text-needs" />
      </span>
    </a>
  );
}
