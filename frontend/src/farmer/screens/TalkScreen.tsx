import { Icon } from "../components/Icon";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import type { TalkView } from "../view-models/types";

function DecisionsLink({ view }: { view: TalkView }) {
  if (view.decision === null) return null;
  return (
    <a
      href={hrefOf({ screen: "decide", taskId: view.decision.taskId })}
      className="flex min-h-16 items-center justify-between gap-2.5 rounded-control border-[2.5px] border-needs bg-surface px-4 text-ink no-underline"
    >
      <span className="flex flex-col">
        <span className="text-body font-extrabold">{en.talk.decisionsWaiting(view.waitingCount)}</span>
        <span className="text-caption text-ink-3">{view.decision.question}</span>
      </span>
      <Icon name="forward" size={22} strokeWidth={2.6} className="text-needs" />
    </a>
  );
}

export function TalkScreen({ view }: { view: TalkView }) {
  return (
    <>
      <main className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pt-7 pb-3">
        <h1 className="mx-0.5 text-title font-extrabold tracking-title">{en.talk.title}</h1>
        <DecisionsLink view={view} />
        <span className="flex items-center gap-2 px-1 text-caption leading-snug text-ink-3">
          <Icon name="info" size={18} className="shrink-0" />
          {en.talk.onlyAnswers}
        </span>
      </main>
      <div className="flex shrink-0 flex-col items-center gap-5 px-6 pt-4 pb-4.5">
        <button
          type="button"
          disabled
          aria-label={en.talk.tapToTalk}
          className="flex size-30 cursor-not-allowed items-center justify-center rounded-full border-0 bg-divider text-ink-3 ring-12 ring-ground"
        >
          <Icon name="mic" size={48} strokeWidth={2} />
        </button>
        <span className="text-center text-body font-bold text-ink-2">{view.micNote}</span>
      </div>
    </>
  );
}
