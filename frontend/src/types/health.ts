export interface HealthResponse {
  status: string;
  /** True when the backend runs with MOCK_LLM=1: the chat is off (D063, D072). */
  mock_llm: boolean;
  /** D094: what answers. A replay never claims a live model. */
  llm_mode?: "live" | "replay";
  agent_model?: string | null;
  replay?: { recorded_on: string | null; model: string | null } | null;
  daily_cycle?: string;
  agents?: string[];
}
