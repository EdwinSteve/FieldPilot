import { useEffect, useState } from "react";
import { en } from "../i18n/en";
import { clipLength } from "../lib/lookedAt";
import type { TalkControl } from "../view-models/types";
import { Icon } from "./Icon";

const MAX_QUESTION_CHARS = 2000;
const ROUND_BUTTON = "press flex size-16 shrink-0 items-center justify-center rounded-full border-0";
const FIELD =
  "min-h-16 min-w-0 flex-1 rounded-pill border-2 border-border bg-surface px-5 text-body text-ink placeholder:text-ink-3 disabled:bg-divider disabled:text-ink-3";

function ListeningRow({ onSend }: { onSend: () => void }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setSeconds((now) => now + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="flex items-center gap-2.5">
      <p className="flex min-h-16 min-w-0 flex-1 flex-col justify-center rounded-pill bg-needs-tint px-5 text-needs-text">
        <span className="text-body font-extrabold">
          {en.talk.listening} {clipLength(seconds * 1000)}
        </span>
        <span className="text-caption font-bold">{en.talk.tapToSend}</span>
      </p>
      <button
        type="button"
        aria-label={en.talk.stopAndSend}
        onClick={onSend}
        className={`${ROUND_BUTTON} bg-needs text-surface`}
      >
        <Icon name="stopSquare" size={26} />
      </button>
    </div>
  );
}

interface ChatBarProps {
  control: TalkControl;
  /** Why asking is off; null when the live model can answer. */
  unavailable: string | null;
  showHint: boolean;
}

/** The bottom bar of a chat: type and send, or tap the mic. */
export function ChatBar({ control, unavailable, showHint }: ChatBarProps) {
  const { status, failure, draft, setDraft, sendDraft, toggleMic } = control;
  const hasDraft = draft.trim() !== "";
  const off = unavailable !== null || status === "starting" || status === "thinking";
  const look = off ? "cursor-not-allowed bg-divider text-ink-3" : "bg-primary text-surface";
  const hint = unavailable ?? (showHint ? en.talk.hint : null);

  return (
    <div className="flex shrink-0 flex-col gap-2 border-t border-border bg-ground px-4.5 py-2.5">
      {failure === null ? null : (
        <p
          role="alert"
          className="animate-notice-in rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text"
        >
          {failure}
        </p>
      )}
      {hint === null ? null : (
        <p className="px-1 text-center text-caption font-bold text-ink-2">{hint}</p>
      )}
      {status === "listening" ? (
        <ListeningRow onSend={toggleMic} />
      ) : (
        <form
          className="flex items-center gap-2.5"
          onSubmit={(event) => {
            event.preventDefault();
            sendDraft();
          }}
        >
          <input
            type="text"
            aria-label={en.talk.yourQuestion}
            placeholder={en.talk.typeHere}
            value={draft}
            disabled={off}
            maxLength={MAX_QUESTION_CHARS}
            enterKeyHint="send"
            autoComplete="off"
            onChange={(event) => setDraft(event.target.value)}
            className={FIELD}
          />
          {hasDraft ? (
            <button
              type="submit"
              disabled={off}
              aria-label={en.talk.send}
              className={`${ROUND_BUTTON} ${look}`}
            >
              <Icon name="send" size={28} strokeWidth={2.4} />
            </button>
          ) : (
            <button
              type="button"
              disabled={off}
              aria-label={en.talk.tapToTalk}
              onClick={toggleMic}
              className={`${ROUND_BUTTON} ${look}`}
            >
              <Icon name="mic" size={30} strokeWidth={2.2} />
            </button>
          )}
        </form>
      )}
    </div>
  );
}
