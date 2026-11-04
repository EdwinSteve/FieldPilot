# Recorded model responses

Replayed by `MockLLMClient` when `MOCK_LLM=1` (D063, D076). Only the daily
cycle uses them; the chat answers 503 in mock mode, because a recording cannot
answer an arbitrary question.

| File | Content |
|---|---|
| `demo/2026-11-02.json` | Day 1 (Spanish), recorded from `muse-spark-1.3` with the agronomist leading (D093): the zone is dry and 12 mm of rain is forecast; the gate holds the 20 mm irrigation for approval, and the agronomist adds a scouting visit |
| `demo/2026-11-03.json` | Day 2, after the farmer's rejection, a 48 h drought and "+1 día": 20 mm irrigated autonomously, a 20 mm extra irrigation scheduled with notice, and urea (100 kg/ha) proposed now that no rain is coming, waiting for approval |
| `demo-en/*.json` | The same two days in English. On day 2 the agronomist cancels its own stress alert of day 1 and raises a new one |
| `*/RECORDED.json` | The replay's label, shown by the REPLAY badge: date, model and cycle mode (D094) |

The daily cycle replays the file of the plot's current local day. A replay
reproduces the recorded run only on the farm `make seed` builds, and only if
the dashboard actions follow `docs/demo.md`, because the tools read the
database. Re-record with `make record-demo` (real model, needs the key) after
changing a prompt, the seed or the demo steps.
