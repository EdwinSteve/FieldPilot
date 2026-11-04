// The Talk conversation kept across a reload of the tab. Pure logic only.
import type { ChatExchange } from "../view-models/types";
import type { LookedAt } from "./lookedAt";

/** Enough to scroll back through; older questions fall off. */
const MAX_EXCHANGES = 50;

export function toStoredChat(exchanges: readonly ChatExchange[]): string {
  return JSON.stringify(exchanges.slice(-MAX_EXCHANGES));
}

function isLookedAt(value: unknown): value is LookedAt {
  return value === "soil" || value === "rain";
}

function isExchange(value: unknown): value is ChatExchange {
  if (typeof value !== "object" || value === null) return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "number" &&
    (item.durationMs === null || typeof item.durationMs === "number") &&
    typeof item.question === "string" &&
    (item.answer === null || typeof item.answer === "string") &&
    Array.isArray(item.lookedAt) &&
    item.lookedAt.every(isLookedAt) &&
    (item.offTopic === undefined || typeof item.offTopic === "boolean")
  );
}

/** The saved conversation, or none when the text is missing or not what this app wrote. */
export function fromStoredChat(text: string | null): ChatExchange[] {
  if (text === null) return [];
  try {
    const parsed: unknown = JSON.parse(text);
    return Array.isArray(parsed) && parsed.every(isExchange) ? parsed : [];
  } catch {
    return [];
  }
}
