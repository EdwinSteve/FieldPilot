export interface HealthResponse {
  status: string;
  /** True when the backend runs with MOCK_LLM=1: the chat is off (D063, D072). */
  mock_llm: boolean;
}
