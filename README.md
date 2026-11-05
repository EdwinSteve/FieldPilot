# FieldPilot 🌱

**An AI agent that runs a crop cycle the way a careful farmer would.**
It reads soil sensors and satellite imagery, makes most operational decisions
on its own within safe limits, asks the farmer before anything that changes
the economics or the land, and explains every decision in plain language.

> Built during the Meta Global AI Developer Hackathon (Oct 26 – Nov 4, 2026).
> Track: Indie Developer · Theme: *Build for Your World*

---

## For judges

Two ways to see FieldPilot work. Every screen shows which one is running:
**LIVE · Muse Spark** or **REPLAY · recorded on … with …**. The badge comes
from `GET /health` ([D094](docs/decisions.md)).

| | With your own Meta Model API key (live) | Without a key (labeled replay) |
|---|---|---|
| Setup | `cp .env.example .env`, set `MOCK_LLM=0` and `MUSE_API_KEY=…` | `cp .env.example .env` (keeps `MOCK_LLM=1`) |
| Check | `make preflight` confirms the key can use every configured model | — |
| Run | `make demo` (installs, seeds the demo farm if there is none, starts both) | the same |
| Open | <http://localhost:5173> the farmer app · `/market` the store · `/dashboard` the agents' timeline and the LIVE/REPLAY badge | the same |
| What you see | Every agent turn is a live Muse Spark call: the agronomist and its specialists, the farmer's chat, the store's assistant | The daily cycle replays a real recorded Muse Spark run (`data/fixtures/llm/demo-en/`); the chat and the store's assistant need the live model |

The key stays in `.env`, which git ignores; CI fails if a secret is tracked.

**A 3-minute route** (details in [`docs/demo.md`](docs/demo.md)):
1. **Plan** (stage 1). Register, then create a plot. The backend downloads
   its weather history (NASA POWER), soil (SoilGrids) and El Niño index
   (ONI), and the trained planner ranks what to sow and when.
2. **Run the farm** (stage 2). Press "Run daily cycle". The **agronomist**,
   the orchestrator, consults its specialists one by one:
   - monitoring (water);
   - imaging (satellite NDVI and SAM 3.1 segmentation);
   - crop health (disease risk from the zone's air);
   - soil nutrition (pH and N-P-K);
   - irrigation.

   It then proposes what crosses domains: a fertilizer that waits for your
   approval, or a scouting visit. Reporting writes the day's report. The
   timeline shows each agent's turns, tools and tokens. Every action passed
   the autonomy gate, and every number in a report was checked against what
   the agents read.
3. **Sell** (stage 3). Harvest, take the lot to the warehouse, and buy it in
   the store. The shopping assistant recommends from your history, and the
   lot's public passport shows how it was grown.

---

## What it does in one picture

```mermaid
flowchart LR
    F[👨‍🌾 Farmer] -- "voice or text" --> A((🤖 FieldPilot Agent))
    A -- "reads" --> D[(Sensors · Satellite · Forecast · Crop catalog)]
    A -- "decides" --> S{🛡️ Autonomy Gate}
    S -- "autonomous" --> X[⚙️ Execute and log]
    S -- "notify" --> N[🔔 Execute and notify farmer]
    S -- "approval" --> Q[✋ Wait for farmer approval]
    X & N & Q --> C[📅 Calendar + event log]
    A -- "writes" --> R[📝 Stage report in the farmer's language]
```

The agent **decides** most things on its own. A deterministic gate checks
every action against its autonomy level and safety rules before it runs.
The farmer always sees **what** happened and **why**.

---

## What the agent looks at

```mermaid
flowchart TB
    AG((🤖 Agent))
    AG --> M[📡 Soil moisture sensors]
    AG --> T[🌡️ Temperature & humidity]
    AG --> W[🌧️ Rain forecast · Open-Meteo]
    AG --> N[🛰️ Satellite NDVI · Sentinel-2]
    AG --> I[🖼️ Plot image · SAM 3.1 segmentation]
    AG --> K[📚 Crop catalog · stage needs]
```

| Source | What it tells the agent | Used for |
|---|---|---|
| Soil moisture | Water available in the root zone | Irrigation decision |
| Temperature & humidity | Growing conditions | Stage progress, stress alerts |
| Rain forecast | Rain expected in the next 24 h | Blocking unnecessary irrigation |
| NDVI (satellite) | Vegetation health over time | Detecting stress before it shows |
| Plot image | Outline and visible crop condition | Plot boundaries, imaging report |
| Crop catalog | Water and nutrient needs per stage | Deciding how much and when |

---

## The agent team

The daily cycle is led by an orchestrator, the **agronomist**
([D093](docs/decisions.md)). It decides which specialists to consult and
reasons across their findings. Each specialist reads its own data and
returns a verified result. Only the agronomist and irrigation can propose
actions, and every proposal goes through the autonomy gate.

```mermaid
flowchart TB
    AG((🧑‍🌾 Agronomist<br/>orchestrator))
    AG -- consult --> MO[💧 Monitoring<br/>soil moisture]
    AG -- consult --> IM[🛰️ Imaging<br/>NDVI · SAM 3.1]
    AG -- consult --> CH[🍃 Crop health<br/>humid-leaf hours · vigor]
    AG -- consult --> SN[🧪 Soil nutrition<br/>pH · N-P-K]
    AG -- consult --> IR[🚿 Irrigation<br/>proposes water]
    AG -- consult --> RE[📝 Reporting<br/>the farmer's report]
    AG -- "propose_task · cancel_task<br/>(fertilizer, agrochemical, scouting, alert)" --> G{🛡️ Autonomy gate}
    IR -- propose_action --> G
    G --> T[📅 Tasks: run, notify, or wait for the farmer]
```

| Agent | Reads | Decides |
|---|---|---|
| Agronomist | the brief of every specialist, open tasks | which specialists to consult; fertilizer, agrochemical, scouting visit, stress alert; edits or cancels its own tasks |
| Monitoring | soil moisture, field capacity, forecast, crop stage | dry, ok or wet per zone |
| Imaging | Sentinel-2 NDVI, SAM 3.1 boxes | low vigor and bare soil per zone |
| Crop health | 48 h of temperature and humidity, imaging | disease, pest and stress risk per zone |
| Soil nutrition | pH and organic carbon (SoilGrids), N-P-K probe (simulated) | deficits against the crop's targets |
| Irrigation | moisture, forecast, root depth | irrigation volumes, through the gate |
| Reporting | the brief, the tasks | the day's report, checked number by number |
| Chat orchestrator | the same reads, read-only | answers the farmer's questions ([D057](docs/decisions.md)) |

## What the agent can do

```mermaid
flowchart LR
    subgraph Monitoring
        M1[Read sensors] --> M2[Flag anomalies]
    end
    subgraph Irrigation
        I1[Propose volume] --> I2{Safety check}
        I2 -- ok --> I3[Open valve]
        I2 -- blocked --> I4[Log reason]
    end
    subgraph Imaging
        G1[Segment plot] --> G2[Assess crop state]
    end
    subgraph Reporting
        R1[Summarize stage] --> R2[Write report in the farmer's language]
    end
    subgraph Planning
        P1[Propose task] --> P2{Autonomy level?}
        P2 -- autonomous --> P3[Schedule]
        P2 -- notify --> P4[Schedule and notify]
        P2 -- approval --> P5[Wait for farmer]
    end
```

### Autonomy levels

The agent acts on its own where the risk is low and reversible. It asks first
where a decision changes the economics of the farm, the soil, or what the
farmer sells.

| Level | What the agent does | Examples | Farmer's role |
|---|---|---|---|
| **Autonomous** | Acts and records the reason | Irrigation within limits, stress alerts, stage reports, calendar updates | Can review the log |
| **Notify** | Acts and sends a notice; the farmer can undo within a time window | Small extra irrigation, calendar shifts of up to 2 days, pest scouting visits | Can revert within 6 hours of simulated time |
| **Approval** | Proposes and waits; does not act until confirmed | Fertilizer and agrochemicals, planting date changes, harvest timing, listing a product for sale, price changes | Accepts or rejects with one tap |

Chemical injection is never automated. Fertilizer and agrochemical tasks always
sit in the approval level.

**What "revert" means** ([D007](docs/decisions.md)). The window is measured on
the simulated clock, and the backend alone decides whether it is open. A
paused clock pauses the window.

- A scheduled task is cancelled before anything runs.
- A running irrigation is stopped, and the water already applied is recorded
  in millimetres and litres.
- Water that has already been applied cannot be undone, so that revert is
  refused and logged.

A scheduled task is checked again by the autonomy gate when its time comes.
If the new verdict needs approval, for example because rain is now forecast,
the task does not run, and the farmer is told which rule changed
([D033](docs/decisions.md)). After a restart, nothing runs a second time. An
irrigation the restart may have cut is reported with its amount as unknown
([D013](docs/decisions.md), [D032](docs/decisions.md)).

### Safety rules

Enforced in code (`backend/app/safety/rules.py`) and covered by tests. They
apply at every autonomy level.

| Rule | Default |
|---|---|
| Max irrigation per zone per day | 20 mm |
| Skip irrigation if rain forecast (24 h) exceeds | 5 mm |
| Minimum interval between irrigations per zone | 12 h |
| Do not irrigate above field-capacity threshold | 85 % |
| Emergency stop | Global flag, checked before every action |

Any action that would exceed these limits is downgraded to the approval level,
not executed. Example: an extra irrigation of 25 mm in one day becomes a
pending approval for the farmer.

---

## The life of a maize crop

The agent follows the crop through its stages and adjusts the calendar at each one.

```mermaid
flowchart LR
    S0[🌱 Sowing] --> S1[🌿 Germination<br/>& emergence]
    S1 --> S2[🌾 Vegetative<br/>growth]
    S2 --> S3[🌽 Flowering]
    S3 --> S4[🌽 Grain fill]
    S4 --> S5[🍂 Maturity<br/>& harvest]
    S5 --> S6[📝 Final report]
```

| Stage | Starts at (°C·day) | Kc | Moisture target (% FC) | Typical tasks on the calendar | Autonomy level |
|---|---|---|---|---|---|
| Sowing | 0 | 0.30 | 60–80 | Prepare soil, sow, first irrigation | Sowing date: approval · Irrigation: autonomous |
| Germination (to emergence) | 20 | 0.30 | 65–80 | Monitor moisture, check emergence | Autonomous |
| Vegetative growth | 55.6 | 0.30 → 1.20 (V3 → V12) | 55–80 | Irrigation schedule, nitrogen fertilizer | Irrigation: autonomous · Fertilizer: approval |
| Flowering | 788.9 | 1.20 | **70**–80 | Strict moisture monitoring, stress alerts | Autonomous (alerts) · Extra irrigation: notify |
| Grain fill | 936.7 | 1.20 | 60–80 | Irrigation adjustment, pest scouting | Irrigation: autonomous · Scouting visit: notify |
| Maturity & harvest | 1291.1 | 1.20 → 0.60 | 40–70 | Stop irrigation, harvest date, traceability record | Harvest date: approval · Irrigation: notify · Stop irrigation: autonomous |

Physiological maturity (black layer) is reached at 1472.2 °C·day. The catalog
is [`config/crops/maize.yaml`](config/crops/maize.yaml).

Kc follows its own FAO-56 curve, independent of the stages (D030): 0.30
until V3 (192.2 °C·day), rising to 1.20 at effective full cover, V12
(566.7), flat until R5 (1291.1), then falling to 0.60 at R6 (1472.2).

**How to read the numbers.**

- **Degree-days and Kc.** Stage thresholds come from Ohio State AGF-0101
  Table 1 (adapted from Iowa State PMR 1009 and Nielsen 2021), which
  publishes them in °F·day. They were converted with °C·day = °F·day ÷ 1.8;
  for example, VE is 100 ÷ 1.8 = 55.6. Daily GDD use the Modified 86/50 °F
  method as published by Purdue. Kc values come from FAO-56 Table 12. Both
  were checked against those sources on 2026-10-28 (D031).
- **Kc ini is verified against the online edition of FAO-56.** The 0.30 used
  at sowing is the cereals group value, inherited by the maize row. The
  original PDF was not checked (D031).
- **Kc curve points are a project mapping.** FAO-56 places them by ground
  cover and maturity, not by leaf stage. V3, V12 and R5 were chosen, the
  earlier stage where the window is uncertain. That overestimates ET, and so
  applies more water than needed, in V3–V6 and V12–V15; the 20 mm/day cap
  bounds the effect (D030).
- **Sowing–germination boundary.** The 20 °C·day start of germination is a
  project decision, not agronomic data. The sources define no boundary
  between sowing and germination.
- **Not agronomist-reviewed.** These are reference values for US Corn Belt
  hybrids and FAO standard conditions. They are not reviewed by an
  agronomist and must be calibrated with local data, for example for Neiva,
  Huila, before real use (D017, D020).
- **Moisture targets and nutrient amounts.** These are demo values with no
  agronomic source.
- **Flowering.** It has the highest moisture floor, because it is the
  stage most sensitive to water stress.
- **Maturity and the 70 % ceiling.** The 40–70 % range at maturity is a
  *target* that lets the grain dry. It is not a safety limit. The safety
  rule ("do not irrigate above 85 % of field capacity") still applies
  everywhere. Irrigation at maturity is raised to *notify*, so the farmer
  sees any watering at that stage.

Stages are estimated from accumulated degree-days, so the calendar updates
when the real weather is hotter or cooler than expected. Changes to the
calendar that move a task more than 2 days are downgraded to approval.

---

## Two days in the life of the agent

The demo follows two simulated days on the demo farm in Neiva (D076). The agent
decides; the autonomy gate checks every proposal; the farmer has the last word.

```mermaid
sequenceDiagram
    autonumber
    participant F as Farmer
    participant A as Agent (daily cycle)
    participant S as Sensors & Satellite
    participant G as Autonomy Gate
    participant V as Valve

    Note over A,S: Day 1 — 2 Nov, 06:00. Rain forecast: 12 mm
    A->>S: Read moisture, forecast, crop stage, NDVI
    S-->>A: Zona 2 dry · 12 mm of rain coming · low vigour on the image
    A->>G: Propose irrigation today (autonomous)
    G-->>F: Held for approval: forecast rain 12 mm > 5 mm limit
    F->>G: Reject: "Esperaré la lluvia"

    Note over S,A: Drought scenario injected, then the clock moves to day 2
    Note over A,S: Day 2 — 3 Nov, 06:00. No rain forecast
    A->>S: Read again
    S-->>A: Zona 2 drier · no rain
    A->>G: Propose irrigation today (autonomous)
    G-->>V: Within every limit · the valve opens
    A->>G: Propose extra irrigation for tomorrow (notify)
    G-->>F: Notice: scheduled, revertible for 6 h of simulated time
    F->>G: Revert
    G-->>A: Reverted before it ran · nothing applied
    A->>F: Daily report, every number checked against the readings
```

The farmer can also ask by text or voice at any moment; the chat answers from
verified readings and never acts (D057). Fertilizer proposals, with their
mandatory approval, are planned after the hackathon.

---

## Quick start

**Prerequisites:** [uv](https://docs.astral.sh/uv/) (manages Python 3.12, see
[D002](docs/decisions.md)), Node.js 24 (`frontend/.nvmrc`), `make`.

**Fastest start:** `make demo`, then open <http://localhost:5173>. It copies
`.env.example` to `.env` if there is none (mock mode), installs the locked
dependencies, builds the demo farm only if no database exists yet, and starts
the backend and the frontend.

| Address | What it is |
|---|---|
| <http://localhost:5173> | The farmer app |
| <http://localhost:5173/market> | The marketplace |
| <http://localhost:5173/dashboard> | The operator dashboard |

```bash
cp .env.example .env        # add your Meta Model API key, or keep MOCK_LLM=1
make install
make dev                    # backend :8000 · frontend :5173 (make dev BACKEND_PORT=8001 if 8000 is taken)
make test                   # backend tests, mock mode, no network
make e2e                    # the whole season over HTTP, fake Muse on localhost (D090)
make e2e-live               # the same season against the real Muse (.env key, quota; D091)
make check                  # what CI runs: hygiene, backend and frontend
```

**The demo:** `make seed`, then `make dev`, then follow
[`docs/demo.md`](docs/demo.md). `make seed` rebuilds the demo farm (fresh
database, maize cycle, clock paused on 2 Nov, 06:00 in Neiva); stop
`make dev` first. In mock mode the two recorded days replay offline, one per
simulated day, on the same clicks the script lists (D076).
`make record-demo` records them again against the real model.

For a live demo, `APP_PROFILE=demo DEMO_REVERT_WINDOW_SECONDS=600` shortens
the revert window. It can only shorten the window, every shortening is logged,
and any other profile refuses to start with the variable set
([D010](docs/decisions.md), [D036](docs/decisions.md)).

Without an API key, the agent runs in **mock mode**: the daily cycle replays
the recorded demo, and the simulator, calendar and autonomy gate work as
usual. The chat and voice need the key (`MOCK_LLM=0`).

---

## Status

[![CI](https://github.com/EdwinSteve/FieldPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/EdwinSteve/FieldPilot/actions/workflows/ci.yml)

All eleven build steps are complete; the two-day demo is in
[`docs/demo.md`](docs/demo.md) and the plan that got here in
[`docs/roadmap.md`](docs/roadmap.md). Every pull request runs the same
Makefile targets as `make check`, in three jobs ([D041](docs/decisions.md)):
- **repository hygiene:** no secret, database or database backup tracked;
- **backend:** ruff with readability rules (complexity, unused code, no
  `print`, no naive datetimes; [D042](docs/decisions.md)), mypy, pytest and
  the end-to-end journey ([D090](docs/decisions.md));
- **frontend:** Oxlint with the React hooks rules, Vitest, and the type-checked
  build ([D068](docs/decisions.md), [D069](docs/decisions.md)).

A box is ticked only when the feature passes its tests. Design decisions are
logged in [`docs/decisions.md`](docs/decisions.md).

- [x] 1. Scaffold: backend, frontend, Makefile, architecture and decision docs
- [x] 2. Domain models and SQLite persistence
- [x] 3. Field simulator with accelerated clock and scenarios
- [x] 4. Phenology engine (maize)
- [x] 5. Safety rules and autonomy gate
- [x] 6. Simulated actuator and NOTIFY revert window
- [x] 7. Agent orchestrator and subagents
- [x] 8. Satellite NDVI and segmentation
- [x] 9. REST API
- [x] 10. Frontend dashboard
- [x] 11. Demo seed and end-to-end test

---

## Architecture

```mermaid
flowchart TB
    subgraph Farmer["Farmer (dashboard)"]
        V[Voice · Muse Voice Transcribe]
        T[Text]
        D[Approve · reject · revert]
    end
    subgraph Cycle["Daily cycle (fixed order, D044)"]
        SM[Monitoring] --> SI[Imaging · NDVI · SAM 3.1] --> SR[Irrigation] --> SP[Reporting]
    end
    subgraph Chat["Chat (read-only, D057)"]
        O[Orchestrator · Muse Spark]
    end
    subgraph Core
        PE[Phenology Engine]
        AG[Autonomy Gate]
        SC[Safety Rules]
        AC[Actuator]
        EL[(Event Log)]
    end
    V --> O
    T --> O
    O -- consults --> SM
    SR -- propose_action --> AG
    PE --> AG
    AG --> SC
    SC -- allowed --> AC
    SC -- downgraded --> AP[Approval queue]
    D --> AP
    SM & SI & SR & SP & O --> EL
    AG --> EL
    AC --> EL
```

The language model never actuates hardware. Only the Irrigation subagent can
propose an action, and every proposal passes through the autonomy gate, which
applies the autonomy level, then the safety rules. The chat answers from
verified readings and never acts.
Module contracts and the data model are in [`docs/architecture.md`](docs/architecture.md). Building a screen? Start with the API guide, [`docs/api.md`](docs/api.md): login, plots, the plan, sowing, harvest and the public passport, with examples.

**Stack:** Python 3.12 · FastAPI · SQLite · React · Vite · pytest
**Models:** Muse Spark (agent) · Muse Voice Transcribe (speech) · SAM 3.1 (segmentation)
**Data:** Open-Meteo (forecast) · Sentinel-2 (cached for the demo)

---

## Scope and limitations

- Sensors are **simulated** in the demo. The interface is built for real hardware but has not been tested with it.
- Satellite imagery is **cached**. Live retrieval is not part of the demo.
- Crop parameters are reference values, each with its source in the YAML. They are not calibrated for local conditions and have not been reviewed by an agronomist ([D017, D020](docs/decisions.md)).
- Autonomy levels and thresholds are defaults for the demo. A real deployment would let each farm adjust them within safe bounds.
- No payments or marketplace in this version.

## Roadmap

- [ ] Real sensor adapters (MQTT)
- [ ] Live satellite retrieval
- [ ] Stage 1: a crop planner that recommends what to sow and when, trained during the hackathon ([planner/](planner/README.md), D079)
- [ ] Stage 3: a direct market with per-lot traceability, warehouses and a shopping agent ([docs/market.md](docs/market.md), D080)
- [ ] Offline mode with Muse Spark Open or Glimmer
- [ ] Approval actions from a mobile notification

## Team

- Edwin Suarez: software architecture, agent orchestration
- Nicholas Putra Halim: frontend developer, farmer app and marketplace design (UI/UX)

## License

MIT