# End-to-end journey (D090)

One farmer's season, from the planner's recommendation to a paid and
delivered order, over HTTP:

```bash
make e2e            # about 6 s; no network, no key
```

## What runs

| Process | What it is |
|---|---|
| The backend | The real app under uvicorn, in its own process. It uses a fresh SQLite file, `APP_PROFILE=demo`, `AUTH_REQUIRED=1` and `MOCK_LLM=0` |
| The fake Muse (`fake_muse/`) | The OpenAI Responses API on localhost. Deterministic doubles play the agents, and SAM replays its recording |

**How the doubles work.** Each one reads with the real tools and closes
with what they returned. The backend's checks (citations, prices, scope)
run exactly as with the model. `GET /_e2e/log` on the fake Muse lists every
turn and any refusal.

## The steps (`test_journey.py`)

| Step | What it checks |
|---|---|
| 1 | Register a farmer, create a plot, read the trained planner's plan, sow maize |
| 2 | The demo sensor kit reports from the first tick |
| 3 | The daily cycle (monitoring, imaging, irrigation, reporting) finds the dry zone; the irrigation runs and the moisture rises |
| 4 | Degree-days count from the recorded temperatures |
| 5 | The chat answers about the field, and refuses off-topic questions with the fixed text |
| 6 | The harvest creates a lot with a verified passport |
| 7 | The lot is listed, dispatched and received at the Bogotá warehouse |
| 8 | The shopping assistant proposes a cart; the customer buys, the operator delivers, the farmer is paid, and the passport shows the sale |
| 9 | Near the best-before day, the product is marked down by itself |
| 10 | No agent turn was refused by the backend's checks |

## When a step fails

The steps share one season and run in order, so a failure stops the rest.

- **Read the assertion first.** A failed request shows the backend's own
  answer.
- **The two logs** are in pytest's temporary directory: `muse.log` and
  `backend.log`.

## Later

When the store and Plan screens exist, Playwright (`pytest-playwright`) can
drive the frontend against these same two processes.
