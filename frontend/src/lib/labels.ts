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

export const ZONE_STATUS_LABELS: Record<string, string> = {
  dry: "Seca",
  ok: "Bien",
  wet: "Húmeda",
};

export const OUTCOME_LABELS: Record<string, string> = {
  execute: "Ejecutada",
  execute_notify: "Programada con aviso",
  await_approval: "Pendiente de aprobación",
};

export const RULE_LABELS: Record<string, string> = {
  emergency_stop_active: "Parada de emergencia",
  always_approval_type: "Siempre requiere aprobación",
  daily_irrigation_cap_exceeded: "Tope diario de riego",
  rain_forecast_above_limit: "Lluvia prevista",
  irrigation_interval_too_short: "Intervalo entre riegos",
  moisture_above_limit: "Humedad sobre el límite",
  calendar_shift_too_large: "Cambio de calendario mayor",
  missing_input: "Falta un dato",
};


export const EVENT_KIND_LABELS: Record<string, string> = {
  proposal: "Propuesta",
  gate_verdict: "Veredicto del gate",
  execution_requested: "Ejecución pedida",
  execution: "Ejecución",
  execution_failed: "Fallo de ejecución",
  revert: "Reversión",
  revert_refused: "Reversión denegada",
  approval: "Aprobación",
  rejection: "Rechazo",
  notification: "Aviso",
  emergency_stop: "Parada de emergencia",
  stage_transition: "Etapa del cultivo",
  agent_tool_call: "Agente",
  config_override: "Cambio de config",
  clock_changed: "Reloj",
  scenario_injected: "Escenario",
  phenology_gap: "Hueco de datos",
};
