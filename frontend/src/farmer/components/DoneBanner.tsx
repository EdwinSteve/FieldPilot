import { en } from "../i18n/en";
import { Icon } from "./Icon";

/**
 * What the farmer's last tap did, at the top of the screen. It stays until the farmer closes it or
 * does the next thing: a message that fades on a timer is gone before a slow reader reaches it.
 */
export function DoneBanner({ text, onClose }: { text: string; onClose: () => void }) {
  return (
    <output
      className="flex shrink-0 animate-notice-in items-center gap-3 rounded-card bg-tint py-1.5 pr-1.5 pl-4 text-primary-hover"
    >
      <span className="flex size-9 shrink-0 animate-pop-in items-center justify-center rounded-full bg-primary text-surface">
        <Icon name="check" size={20} strokeWidth={3} />
      </span>
      <span className="flex-1 py-2 text-body font-extrabold leading-snug">{text}</span>
      <button
        type="button"
        aria-label={en.plan.closeMessage}
        onClick={onClose}
        className="press flex size-12 shrink-0 items-center justify-center rounded-control border-0 bg-transparent text-primary-hover"
      >
        <Icon name="close" size={22} strokeWidth={2.6} />
      </button>
    </output>
  );
}
