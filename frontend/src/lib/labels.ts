// Farmer-facing names for codes the backend sends. Text only, no logic.
// English, the product's language (D084).

export const ACTION_LABELS: Record<string, string> = {
  irrigation: "Irrigation",
  extra_irrigation: "Extra irrigation",
  stop_irrigation: "Stop irrigation",
  stress_alert: "Stress alert",
  stage_report: "Stage report",
  calendar_shift: "Calendar shift",
  scouting_visit: "Scouting visit",
  fertilizer: "Fertilizer",
  agrochemical: "Agrochemical",
  planting_date_change: "Planting date change",
  harvest_timing: "Harvest date",
  product_listing: "Product listing",
  price_change: "Price change",
  chemical_injection: "Chemical injection",
};

export const STATUS_LABELS: Record<string, string> = {
  pending_approval: "Pending",
  scheduled: "Scheduled",
  executed: "Executed",
  reverted: "Reverted",
  rejected: "Rejected",
  failed: "Failed",
  cancelled: "Cancelled",
};

export const LEVEL_LABELS: Record<string, string> = {
  autonomous: "Autonomous",
  notify: "With notice",
  approval: "With approval",
};

export const ZONE_STATUS_LABELS: Record<string, string> = {
  dry: "Dry",
  ok: "Fine",
  wet: "Wet",
};

export const OUTCOME_LABELS: Record<string, string> = {
  execute: "Executed",
  execute_notify: "Scheduled with notice",
  await_approval: "Awaiting approval",
};

export const RULE_LABELS: Record<string, string> = {
  emergency_stop_active: "Emergency stop",
  always_approval_type: "Always needs approval",
  daily_irrigation_cap_exceeded: "Daily irrigation cap",
  rain_forecast_above_limit: "Rain forecast",
  irrigation_interval_too_short: "Interval between irrigations",
  moisture_above_limit: "Moisture above the limit",
  calendar_shift_too_large: "Calendar shift too large",
  missing_input: "A value is missing",
};


export const EVENT_KIND_LABELS: Record<string, string> = {
  proposal: "Proposal",
  gate_verdict: "Gate verdict",
  execution_requested: "Execution requested",
  execution: "Execution",
  execution_failed: "Execution failed",
  revert: "Revert",
  revert_refused: "Revert refused",
  approval: "Approval",
  rejection: "Rejection",
  notification: "Notice",
  emergency_stop: "Emergency stop",
  stage_transition: "Crop stage",
  agent_tool_call: "Agent",
  config_override: "Config change",
  clock_changed: "Clock",
  scenario_injected: "Scenario",
  phenology_gap: "Data gap",
  planting_plan_served: "Planting plan",
  cycle_started: "Sowing confirmed",
  harvest_confirmed: "Harvest confirmed",
  lot_commissioned: "Lot created",
};
