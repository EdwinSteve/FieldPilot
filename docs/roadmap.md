# FieldPilot Roadmap: the agent phase (steps 7–11)

- **Written:** 2026-10-29
- **Deadline:** 2026-11-04 (Meta Global AI Developer Hackathon)
- **Owner of the plan:** the whole team. Decisions referenced here live in
  [`decisions.md`](decisions.md); module contracts live in
  [`architecture.md`](architecture.md).

This document says what is built, what remains, and how the Muse agents fit
on top of what exists. It follows the patterns taught in the Meta workshop
[`meta-models/legal-agent-workshop`](https://github.com/meta-models/legal-agent-workshop),
adapted to a crop-management agent.

---

## 1. Where we are

Steps 1–6 are merged in `main`, with CI on every pull request (D041, D042)
and 593 tests passing.

| Area | What exists | Decisions |
|---|---|---|
| Safety | Pure rules with boundary tests; emergency stop | D001, D004, D022, D026, D027 |
| Autonomy | Three-level gate; stage overrides only tighten; startup refuses unsafe config | D005, D006, D025 |
| Execution | Gate-issued `ExecutionPermit`; simulated actuator; write-ahead execution; startup reconciliation | D013, D032, D037, D039 |
| Revert | NOTIFY window in simulated time; re-evaluation when a scheduled task is due | D007, D009, D011, D033, D040 |
| Field | Simulator with accelerated clock and scenarios; maize phenology from cited sources | D014, D016, D017–D021, D030, D031 |
| Audit | Append-only event log; every decision has inputs, level, rule and reason | D012, D013, D023 |

**Not built yet.** These are the gaps this roadmap closes:

- the Muse client;
- the agent loop, the tools and the subagents;
- the rain forecast adapter (`RainForecast` has no implementation, so every
  irrigation is held for approval by D027);
- NDVI, SAM 3.1 segmentation and voice;
- the REST API and the dependency container;
- the dashboard;
- the demo seed.

## 2. Models available to the team

Confirmed with `GET https://api.meta.ai/v1/models` on 2026-10-29.

| Use | Model id | Setting |
|---|---|---|
| Agent reasoning and tool use | `muse-spark-1.3` | `MUSE_AGENT_MODEL` |
| Segmentation (crop, soil, weeds) | `sam-3.1` | `MUSE_SEGMENTATION_MODEL` |
| Farmer voice input | `muse-voice-transcribe-1.0` | `MUSE_TRANSCRIBE_MODEL` |

All three are reached through the official OpenAI Python SDK, pointed at
`MUSE_API_BASE_URL=https://api.meta.ai/v1` (D043). Model ids come from the
environment and are never hardcoded. With `MOCK_LLM=1`, nothing reaches the
network.

## 3. What the workshop teaches, and where it lands here

| Workshop pattern | FieldPilot | Status |
|---|---|---|
| `responses.create` with `store=False`; the full conversation is sent each turn | `MuseClient` behind the `LLMClient` port | Step 7a |
| One tool per turn (`parallel_tool_calls=False`); turn limit; last-turn nudge; `paused` on API failure; `resume` | `AgentLoop`, shared by every subagent | Step 7a |
| One file per tool: a definition the model sees, plus `run(ctx, args)`; a refusal returns `{"error": ...}` so the model corrects it | `Tool` with a pydantic input model; `ToolRegistry` | Step 7a |
| **Checks inside the tools, never a separate tool the model may skip** | `propose_action` → `AutonomyGate` (already built); `submit_assessment` and `submit_report` checks | Gate ✅; the rest in step 7b |
| Quotes checked against the page; anything else refused | Every number the agent cites must match a stored observation (reading, forecast, GDD, NDVI) | Step 7b |
| 3 refusals → a person decides | 3 refused reports → the farmer is notified | Step 7b |
| `needs_input` and `awaiting_signoff` | APPROVAL tasks and the NOTIFY revert window | ✅ |
| Progress saved every turn; a console shows plan → act → observe | `agent_tool_call` events; the dashboard timeline | Steps 7a, 10 |
| A fake model for tests | `MockLLMClient`, plus recording and replay of real runs | Step 7a |
| SAM 3.1 through `input_image`, parsing `<\|box;…\|>` tokens | `Sam31Segmentation` behind `SegmentationProvider` | Step 8 |

## 4. How the agents fit together

```
  Daily cycle (triggered by the simulated clock)       Farmer chat (text or voice)
  ┌──────────────────────────────────────────────┐    ┌──────────────────────────────┐
  │ Monitoring → Imaging → Irrigation → Reporting │    │ Orchestrator (Muse Spark)     │
  │ fixed order; the model decides inside each    │    │ consults subagents as tools   │
  └───────────────┬──────────────────────────────┘    └──────────────┬───────────────┘
                  ▼    FieldBrief: observations with ids (readings, forecast, GDD, NDVI)  ▼
        only Irrigation holds propose_action → ProposalService → AutonomyGate → Actuator
```

**One loop engine** (D044). `AgentLoop` is the workshop's loop, written
once. A subagent is configuration, not code: a system prompt, a subset of
tools and a closing tool.

**Hybrid orchestration** (D044).
- **The daily cycle runs the subagents in a fixed order.** That keeps the
  demo deterministic and avoids a routing mistake by the model. Inside each
  subagent, the model chooses every tool call, as in the workshop.
- **In the farmer chat, the orchestrator is itself an agent.** Its tools
  consult subagents and return their structured results.

**Structured handoffs.** Subagents never pass free text to one another.
Each one closes with a validated object that cites observation ids, and
the next subagent reads that object from the `FieldBrief`.

| Subagent | Reads | Closes with | Check inside the closing tool |
|---|---|---|---|
| Monitoring | Readings, forecast, stage and GDD | `submit_assessment` | Every zone covered; every cited value exists and matches what is stored |
| Imaging | NDVI scene and SAM segmentation | `submit_imaging` | The cited scene and mask exist; the reported fractions match the computed ones |
| Irrigation | `FieldBrief` | `propose_action` (one or more), then `finish` | `AutonomyGate`: the agent never reaches the actuator (principle 1) |
| Reporting | `FieldBrief`, verdicts and event log | `submit_report` | Every number matches a recorded fact; no claim of an action without its `execution` event; Spanish text from the catalog where one exists |

**Trace** (D045). Every turn writes one `agent_tool_call` event: run id,
subagent, turn, tool, arguments, result or error, and token usage. No new
table is needed. The dashboard reads these events to draw the timeline.

**Record and replay.** A real run against Muse can be recorded as
fixtures. The demo and the end-to-end tests replay them, so the demo does
not depend on the network, and `MOCK_LLM=1` keeps working without a key.

## 5. Plan, step by step

Each step follows the usual process:

1. a docs commit with the interface, waiting for confirmation;
2. implementation commits, each passing `make check`;
3. mutation checks, with their results in the commit message;
4. a README box ticked only when the tests pass;
5. one pull request per step.

### Step 7a: the loop and the client (2026-10-29 → 10-30)

- **Preflight:** a `make preflight` target checks that the key can use the
  three models. It prints model ids only, never the key.
- **Client:**
  - the `LLMClient` port, with `MuseClient` built on `openai`
    (`responses.create`) and `MockLLMClient` replaying fixtures;
  - `AgentLoop`: turn limit, last-turn nudge, `paused` on API failure,
    and `resume`;
  - `ToolRegistry`: pydantic validation, and refusals returned as
    `{"error": ...}`;
  - one `agent_tool_call` event per turn.
- **Rain forecast:** `FixtureForecast`, built from an Open-Meteo fixture,
  implementing `RainForecast`. It comes first because irrigation is held
  without it.
- **Done when:**
  - a scripted fake model runs plan → act → observe, pauses and resumes;
  - an invalid tool argument comes back as an error the model can correct;
  - no test touches the network.

### Step 7b: subagents and verification (2026-10-30 → 10-31)

- **Subagents:** Monitoring, Irrigation and Reporting, with their tools and
  closing-tool checks; the daily cycle; the chat orchestrator.
- **Escalation:** a report refused three times notifies the farmer instead
  of looping.
- **Record and replay:** `RecordingLLMClient`, and a hand-written fixture
  for the D009 end-to-end test. Recording from real Muse moves to step 11.
- **Done when:**
  - the D009 scenario runs end to end on replayed fixtures: a 15 mm
    irrigation, a 10 mm NOTIFY extra irrigation for the next day, and the
    revert;
  - each closing-tool check refuses a deliberately wrong submission;
  - **mutation checks:** remove each check, and give a read-only subagent
    `propose_action`. Tests must fail.

### Step 8: imaging and voice (2026-10-31 → 11-01)

- **NDVI:** compute it from fixture red and near-infrared bands
  (`compute_ndvi`, pure), plus `ImageryLoader`.
- **Segmentation:** `Sam31Segmentation` (prompt, `input_image`, box
  parsing) and `MockSegmentation`; then the Imaging subagent.
- **Voice (stretch):** `MuseVoiceTranscribe` and `MockSpeechToText`.
- **Done when:** Imaging adds a low-NDVI zone to the `FieldBrief`, and
  Monitoring and Irrigation use it.

### Step 9: REST API (2026-11-01 → 11-02)

- **Container:** `app/container.py` wires every service once, with no
  global mutable state.
- **Routes:** §7 of the architecture. They hold no logic.
  `RevertRefusedError` maps to 409, and every revertible task carries
  `revert_deadline` and `revert_open` (D011).
- **Done when:** API tests cover approve, reject, revert (200 and 409),
  chat, events and the emergency stop.

### Step 10: dashboard (2026-11-02 → 11-03)

- **Views:** the agent timeline (plan → act → observe, from
  `agent_tool_call`), approvals, the revert card worded as D011 requires,
  the calendar, the zones with NDVI, and the D014 restart notice.
- **Frontend lint:** decide whether to add ESLint now (new npm
  dependencies, which need approval under rule 9).
- **Done when:** the whole demo flow is visible in the browser.

### Step 11: seed, end to end and demo (2026-11-03 → 11-04)

- **Seed:** `make seed` builds the demo farm and the maize cycle.
- **End-to-end tests:** the ones required by D009 and D016.
- **Recorded Muse run:** record the D009 demo once against the real model,
  now that `make seed` exists.

The hand-written fixture of step 7b verifies the business logic of D009. A
recording from the real Muse model verifies that the model's output format
stays compatible with the tools. They are different tests, and neither
replaces the other.
- **Delivery:** the demo script, the video, and a final README pass.
- **Done when:** every box in the README Status list is ticked, and the
  demo runs with `MOCK_LLM=1` and with the real key.

## 6. Risks and what we cut first

| Risk | Mitigation |
|---|---|
| API latency or rate limits during the demo | Replayed fixtures by default; live mode is optional |
| `store=False` resends the whole conversation every turn | Small subagents with short turn limits; the `FieldBrief` instead of long histories |
| SAM 3.1 output format changes | One parser with fixture tests; the mock provider stays available |
| Behind schedule | Cut in this order: voice, photo analysis, the chat orchestrator (keeping the daily cycle) |

Never cut, under any schedule:

- the gate in front of every action;
- the closing-tool checks;
- the event trace;
- the tests that keep `make check` green.

## 7. Configuration

Secrets live only in `.env`, which git ignores. `make check-repo` fails if
it is ever tracked. `.env.example` lists every variable with safe defaults:

| Variable | Default | Notes |
|---|---|---|
| `MOCK_LLM` | `1` | `0` uses the real API and requires the key and the model ids |
| `MUSE_API_KEY` | (empty) | Secret. Never logged, never printed |
| `MUSE_API_BASE_URL` | `https://api.meta.ai/v1` | |
| `MUSE_AGENT_MODEL` | `muse-spark-1.3` | |
| `MUSE_SEGMENTATION_MODEL` | `sam-3.1` | Read from step 8 |
| `MUSE_TRANSCRIBE_MODEL` | `muse-voice-transcribe-1.0` | Read from step 8 |
| `APP_PROFILE` | `dev` | `demo` allows `DEMO_REVERT_WINDOW_SECONDS` (D010, D036) |
