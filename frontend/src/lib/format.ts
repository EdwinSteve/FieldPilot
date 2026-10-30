// Spanish formatting for the farmer. Pure functions only.

/** "45 s", "12 min", "1 h 05 min", "2 d 3 h". Negative or NaN count as zero. */
export function formatDuration(totalSeconds: number): string {
  const seconds = Number.isFinite(totalSeconds) ? Math.max(0, Math.floor(totalSeconds)) : 0;
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  if (days > 0) return hours > 0 ? `${days} d ${hours} h` : `${days} d`;
  if (hours > 0) return `${hours} h ${String(minutes).padStart(2, "0")} min`;
  if (minutes > 0) return `${minutes} min`;
  return `${seconds} s`;
}

/** Decimal comma and at most `decimals` decimals, as the backend's catalogue writes: 20.5 -> "20,5". */
export function formatNumber(value: number, decimals = 1): string {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: decimals }).format(value);
}

/** A calendar date as day and month: "2026-10-20" -> "20 oct". */
export function formatDayMonth(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  if (year === undefined || month === undefined || day === undefined) return isoDate;
  if (!Number.isInteger(year) || month < 1 || month > 12 || day < 1 || day > 31) return isoDate;
  return `${day} ${MONTHS[month - 1]}`;
}

/** A UTC instant as local date and time in the plot's offset: "28 oct, 06:00". */
export function formatPlotTime(iso: string, utcOffsetHours: number): string {
  const shifted = new Date(Date.parse(iso) + utcOffsetHours * 3_600_000);
  const day = shifted.getUTCDate();
  const month = MONTHS[shifted.getUTCMonth()];
  const hh = String(shifted.getUTCHours()).padStart(2, "0");
  const mm = String(shifted.getUTCMinutes()).padStart(2, "0");
  return `${day} ${month}, ${hh}:${mm}`;
}

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
