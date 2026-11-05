// Answers given without signal: kept on this phone and sent once the farm answers
// again. api/session clears them on Sign out, with the rest of the farmer's visit.
import { useEffect, useRef, useState } from "react";
import { api } from "../../api/endpoints";
import { en } from "../i18n/en";
import { actionFailure } from "../lib/actionFailure";
import {
  fromStoredOutbox,
  sortOutbox,
  toStoredOutbox,
  withAnswer,
  type SavedAnswer,
} from "../lib/outbox";
import { pendingTasks, type FarmSnapshot } from "../view-models/snapshot";

const OUTBOX_KEY = "fieldpilot.outbox";
/** As long as the other notices: long enough to read. */
const NOTICE_MS = 6_000;

function readOutbox(): SavedAnswer[] {
  try {
    return fromStoredOutbox(window.localStorage.getItem(OUTBOX_KEY));
  } catch {
    return [];
  }
}

type Sent = "sent" | "closed" | "later";

async function send(answer: SavedAnswer): Promise<Sent> {
  try {
    if (answer.answer === "yes") await api.approve(answer.taskId);
    else await api.reject(answer.taskId, answer.reason);
    return "sent";
  } catch (caught) {
    // The farm said no (already answered, say): the answer is spent. No signal: keep it.
    return actionFailure(caught, navigator.onLine) === "rejected" ? "closed" : "later";
  }
}

/** Sends what still waits for the farmer, one at a time; stops at the first that cannot get through. */
async function flush(answers: readonly SavedAnswer[], waiting: ReadonlySet<number>) {
  const { send: toSend, closed } = sortOutbox(answers, waiting);
  const done = new Set(closed.map((answer) => answer.taskId));
  let sent = 0;
  let refused = closed.length;
  for (const answer of toSend) {
    const result = await send(answer);
    if (result === "later") break;
    done.add(answer.taskId);
    if (result === "sent") sent += 1;
    else refused += 1;
  }
  return { done, sent, refused };
}

export interface Outbox {
  answers: SavedAnswer[];
  save: (answer: SavedAnswer) => void;
  /** What the last send did, while it is news. */
  notice: string | null;
}

/**
 * Tries again on each fresh read of the farm while the phone is online, so a
 * read that got through is the sign the answers can too.
 */
export function useOutbox(snapshot: FarmSnapshot | null, online: boolean, onSent: () => void): Outbox {
  const [answers, setAnswers] = useState(readOutbox);
  const [notice, setNotice] = useState<string | null>(null);
  const triedWith = useRef<FarmSnapshot | null>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(OUTBOX_KEY, toStoredOutbox(answers));
    } catch {
      // Private mode: the answers wait only while the app stays open.
    }
  }, [answers]);

  useEffect(() => {
    if (!online || snapshot === null || answers.length === 0 || triedWith.current === snapshot) return;
    triedWith.current = snapshot;
    const waiting = new Set(pendingTasks(snapshot).map((task) => task.id));
    void flush(answers, waiting).then(({ done, sent, refused }) => {
      // Keep any answer saved while these were on their way.
      setAnswers((current) => current.filter((answer) => !done.has(answer.taskId)));
      if (sent > 0) {
        setNotice(en.outbox.sent);
        onSent();
      } else if (refused > 0) {
        setNotice(en.outbox.closed);
      }
    });
  }, [online, snapshot, answers, onSent]);

  useEffect(() => {
    if (notice === null) return undefined;
    const timer = window.setTimeout(() => setNotice(null), NOTICE_MS);
    return () => window.clearTimeout(timer);
  }, [notice]);

  return {
    answers,
    save: (answer) => setAnswers((current) => withAnswer(current, answer)),
    notice,
  };
}
