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

## Against the real Muse: `make e2e-live` (D091)

```bash
make e2e-live       # needs MUSE_API_KEY, MUSE_AGENT_MODEL and MUSE_SEGMENTATION_MODEL in .env
```

The same ten steps run against the Meta Model API. This uses the network and
costs quota, so it never runs in CI. Run it before a demo.

**What it checks:**
- **Exactly:** what the backend guarantees, as in `make e2e`.
- **Reported, not required:** what is the model's judgement. That covers the
  status it gives each zone, how many irrigations it proposes, the words of
  an answer and the cart it proposes.

**The report card.** At the end it prints, for each farm agent, the turns
taken, the answers the checks refused (with the first reason) and the
tokens. It also lists what the model did on each step:

```
=== Muse report card (e2e-live) ===
monitoring      5 turns   0 refused      600 tok
irrigation      5 turns   0 refused      600 tok
...
--- the journey ---
daily cycle: zones {1: 'ok', 2: 'dry'}, 1 proposal(s)
chat off topic: topic 'out_of_scope'
```

Many refusals mean the model and the prompts disagree. Read the first
reason before changing code.

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
