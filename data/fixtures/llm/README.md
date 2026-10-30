# Recorded model responses

Replayed by `MockLLMClient` when `MOCK_LLM=1` (D063). Only the daily cycle
uses them: the chat answers 503 in mock mode, because a fixture cannot
answer an arbitrary question.

| File | Content |
|---|---|
| `demo_day1.json` | Placeholder: the hand-written D009 fixture of step 7b (Monitoring, Imaging, Irrigation, Reporting). Its observation ids assume a fresh database with one plot and one zone. Step 11 replaces it with a recording from the real model on the seeded demo farm. |
