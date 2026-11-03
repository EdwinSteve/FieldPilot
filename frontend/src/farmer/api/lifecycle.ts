// The routes the farmer app needs beyond the dashboard's: login, plots, the plan
// and the sowing (D082, D083, docs/api.md). One function per route, no logic.
import { getJson, postJson } from "../../api/client";
import type { Cycle, Plot } from "../../types/api";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  /** Seconds the access token lasts. */
  expires_in: number;
}

export interface User {
  id: number;
  phone: string;
  full_name: string;
  role: "farmer" | "customer" | "operator" | "admin";
}

export interface Registration {
  phone: string;
  full_name: string;
  password: string;
  role: "farmer";
  accept_privacy_policy: true;
  privacy_policy_version: string;
}

export interface NewPlot {
  name: string;
  municipality: string;
  department: string;
  latitude: number;
  longitude: number;
  area_ha: number;
}

export type SiteStatus = "missing" | "pending" | "ready" | "failed";

export interface PlotSite {
  status: SiteStatus;
  requested_at: string | null;
  finished_at: string | null;
  message: string | null;
  weather_until: string | null;
  built_on: string | null;
}

export interface CropOutlook {
  crop: string;
  name_es: string;
  sowing_date: string;
  harvest_date: string;
  rel_yield_p10: number;
  rel_yield_p50: number;
  rel_yield_p90: number;
  /** The chance the yield reaches 60 % of the potential. */
  p_success: number;
  /** Water on top of the rain, in mm. */
  irrigation_mm_p50: number;
  heat_days: number;
  cold_days: number;
  /** Stage 2 can run it; otherwise the cycle is a manual record. */
  automatable: boolean;
}

export interface SowingWeek {
  sowing_date: string;
  weather_until: string;
  oni: number;
  oni_latest_published: boolean;
  /** Best first; the first three are the recommended ones. */
  outlooks: CropOutlook[];
}

export interface PlantingPlan {
  plot_id: number;
  generated_at: string;
  /** "b0-climatology" when the trained network is not in use. */
  model: string;
  site_built_on: string;
  weeks: SowingWeek[];
}

export interface NewCycle {
  crop: string;
  sowing_date: string;
  accept_own_risk: boolean;
}

/** A cycle as POST /plots/{id}/cycles answers, with how it runs (D083). */
export interface StartedCycle extends Cycle {
  automated: boolean;
  own_risk: boolean;
}

/** A plot as D083 answers, with where it is. */
export interface FarmPlot extends Plot {
  municipality: string | null;
  department: string | null;
}

export const lifecycle = {
  privacyPolicy: () => getJson<{ version: string }>("/auth/privacy-policy"),
  register: (form: Registration) =>
    postJson<{ user: User; tokens: TokenPair }>("/auth/register", form),
  logIn: (phone: string, password: string) =>
    postJson<TokenPair>("/auth/login", { phone, password }),
  me: () => getJson<User>("/auth/me"),
  logOut: (refreshToken: string) =>
    postJson<undefined>("/auth/logout", { refresh_token: refreshToken }),

  plots: () => getJson<FarmPlot[]>("/plots"),
  createPlot: (plot: NewPlot) => postJson<FarmPlot>("/plots", plot),
  site: (plotId: number) => getJson<PlotSite>(`/plots/${plotId}/site`),
  rebuildSite: (plotId: number) => postJson<PlotSite>(`/plots/${plotId}/site`),
  plantingPlan: (plotId: number, weeks: number) =>
    getJson<PlantingPlan>(`/plots/${plotId}/planting-plan?weeks=${weeks}`),
  cycles: () => getJson<StartedCycle[]>("/cycles"),
  startCycle: (plotId: number, cycle: NewCycle) =>
    postJson<StartedCycle>(`/plots/${plotId}/cycles`, cycle),
};
