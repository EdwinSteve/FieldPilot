// Answers to decisions given without signal, kept on the phone until they can be sent. Pure logic only.

export interface SavedAnswer {
  taskId: number;
  answer: "yes" | "no";
  /** The reason given with a no; absent for none. */
  reason?: string;
  /** When the farmer answered, on the phone's clock. */
  savedAt: number;
}

const VERSION = 1;

export function toStoredOutbox(answers: readonly SavedAnswer[]): string {
  return JSON.stringify({ version: VERSION, answers });
}

function isAnswer(value: unknown): value is SavedAnswer {
  const answer = value as Partial<SavedAnswer> | null;
  return (
    typeof answer?.taskId === "number" &&
    (answer.answer === "yes" || answer.answer === "no") &&
    (answer.reason === undefined || typeof answer.reason === "string") &&
    typeof answer.savedAt === "number"
  );
}

export function fromStoredOutbox(text: string | null): SavedAnswer[] {
  try {
    const value = JSON.parse(text ?? "null") as { version?: unknown; answers?: unknown } | null;
    if (value?.version !== VERSION || !Array.isArray(value.answers)) return [];
    return value.answers.filter(isAnswer);
  } catch {
    return [];
  }
}

/** One answer per decision: a later one replaces the earlier. */
export function withAnswer(answers: readonly SavedAnswer[], answer: SavedAnswer): SavedAnswer[] {
  return [...answers.filter((saved) => saved.taskId !== answer.taskId), answer];
}

export function withoutAnswer(answers: readonly SavedAnswer[], taskId: number): SavedAnswer[] {
  return answers.filter((saved) => saved.taskId !== taskId);
}

/**
 * What to do with each saved answer once there is signal: send the ones still
 * waiting for the farmer, and drop the ones the farm has moved past.
 */
export function sortOutbox(
  answers: readonly SavedAnswer[],
  stillWaiting: ReadonlySet<number>,
): { send: SavedAnswer[]; closed: SavedAnswer[] } {
  return {
    send: answers.filter((saved) => stillWaiting.has(saved.taskId)),
    closed: answers.filter((saved) => !stillWaiting.has(saved.taskId)),
  };
}
