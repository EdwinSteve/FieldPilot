// The autonomy policy as the legend shows it: action types grouped by level.
export interface LevelGroups {
  autonomous: string[];
  notify: string[];
  approval: string[];
}

/** Groups action types by their level, sorted; unknown levels are ignored. */
export function groupByLevel(defaults: Record<string, string>): LevelGroups {
  const groups: LevelGroups = { autonomous: [], notify: [], approval: [] };
  for (const [action, level] of Object.entries(defaults)) {
    if (level === "autonomous" || level === "notify" || level === "approval") {
      groups[level].push(action);
    }
  }
  groups.autonomous.sort();
  groups.notify.sort();
  groups.approval.sort();
  return groups;
}
