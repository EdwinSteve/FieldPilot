# Recorded model responses

Replayed by `MockLLMClient` when `MOCK_LLM=1` (D063, D076). Only the daily
cycle uses them; the chat answers 503 in mock mode, because a recording cannot
answer an arbitrary question.

| File | Content |
|---|---|
| `demo/2026-11-02.json` | Day 1 of the demo, recorded from `muse-spark-1.3`: the zone is dry, 12 mm of rain is forecast, the gate holds the 20 mm irrigation for approval |
| `demo/2026-11-03.json` | Day 2, after the farmer's rejection, a 48 h drought and "+1 día": 20 mm irrigated autonomously, and a 20 mm extra irrigation for 4 Nov scheduled with notice |

The daily cycle replays the file of the plot's current local day. A replay
reproduces the recorded run only on the farm `make seed` builds, and only if
the dashboard actions follow `docs/demo.md`, because the tools read the
database. Re-record with `make record-demo` (real model, needs the key) after
changing a prompt, the seed or the demo steps.
