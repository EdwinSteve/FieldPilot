// Neighbouring items that share a key, kept in order. Pure logic only.

export interface Run<T> {
  key: string;
  items: T[];
}

/** Splits a list where the key changes: ["a","a","b","a"] gives three runs. */
export function groupRuns<T>(items: readonly T[], keyOf: (item: T) => string): Run<T>[] {
  const runs: Run<T>[] = [];
  for (const item of items) {
    const key = keyOf(item);
    const last = runs.at(-1);
    if (last !== undefined && last.key === key) last.items.push(item);
    else runs.push({ key, items: [item] });
  }
  return runs;
}
