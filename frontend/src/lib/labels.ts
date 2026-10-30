// Farmer-facing names for codes the backend sends. Text only, no logic.

export const ACTION_LABELS: Record<string, string> = {
  irrigation: "Riego",
  extra_irrigation: "Riego extra",
  stop_irrigation: "Detener riego",
  stress_alert: "Alerta de estrés",
  stage_report: "Informe de etapa",
  calendar_shift: "Cambio de calendario",
  scouting_visit: "Visita de inspección",
  fertilizer: "Fertilización",
  agrochemical: "Agroquímico",
  planting_date_change: "Cambio de fecha de siembra",
  harvest_timing: "Fecha de cosecha",
  product_listing: "Publicación de producto",
  price_change: "Cambio de precio",
  chemical_injection: "Inyección química",
};

export const STATUS_LABELS: Record<string, string> = {
  pending_approval: "Pendiente",
  scheduled: "Programada",
  executed: "Ejecutada",
  reverted: "Revertida",
  rejected: "Rechazada",
  failed: "Fallida",
};

export const LEVEL_LABELS: Record<string, string> = {
  autonomous: "Autónoma",
  notify: "Con aviso",
  approval: "Con aprobación",
};
