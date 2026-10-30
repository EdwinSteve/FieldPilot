# Decision Log

This file records project decisions, especially where a requirement was
ambiguous. When in doubt, the safer option is chosen and written down here.

Each entry is append-only. To change a decision, add a new entry that
supersedes the old one and mark the old one as `Superseded by DNNN`.

**Format:** ID · Date · Status · Context · Decision · Consequences

---

## D001 — Safety limits live in `config/safety.yaml`, separate from `config/autonomy.yaml`

- **Date:** 2026-10-27
- **Status:** Accepted

**Context.** The brief puts the default autonomy level per action type in
`config/autonomy.yaml`. It also requires the safety rules in
`app/safety/rules.py` to be pure functions with no I/O. It does not say where
the numeric limits are configured: 20 mm/day, 5 mm forecast rain, 12 h
interval, 85 % field capacity, and 2-day calendar shift.

**Decision.**
- Autonomy levels go in `config/autonomy.yaml`. Safety limits go in
  `config/safety.yaml`.
- The limits are loaded once, at the edge of the app, into an immutable
  `SafetyLimits` value object.
- That object is passed as an argument to the pure functions in
  `app/safety/rules.py`.

**Consequences.**
- Each file has a single reason to change. Autonomy policy and physical safety
  thresholds are different concerns.
- `rules.py` stays free of I/O and can be tested deterministically with any
  set of limits, including boundary values.
- Changing a threshold needs no code change.
- The config loader must validate `safety.yaml`. A missing or invalid value
  stops the app at startup; it is never silently replaced by a default.
  This is the safer option.

---

## D002 — Use Python 3.12 via `uv`

- **Date:** 2026-10-27
- **Status:** Accepted

**Context.** The brief requires Python 3.12. The development machine's system
interpreter is Python 3.14.

**Decision.**
- `uv` manages the backend environment.
- Python 3.12 is pinned with `backend/.python-version`, and
  `requires-python = ">=3.12,<3.13"` is set in `backend/pyproject.toml`.
- The Makefile runs every backend command through `uv run`.

**Consequences.**
- The interpreter and dependency versions are reproducible for every
  contributor and for CI.
- The system Python is never used or modified.
- `uv` becomes a prerequisite and is documented in the README Quick start.

---

## D003 — Code, documentation and commits in English; farmer-facing reports in Spanish

- **Date:** 2026-10-27
- **Status:** Accepted

**Context.** The brief asks for English docstrings. The README promises stage
reports in Spanish for the farmer.

**Decision.**
- The following are written in English: source code, identifiers, docstrings,
  comments, the docs in `docs/`, the README, and commit messages.
- Stage reports for the farmer are generated in Spanish.
- The report language is a parameter of the reporting module, not hardcoded.

**Consequences.**
- The codebase is readable to the international hackathon jury and to
  contributors.
- The product still meets its user, a Spanish-speaking farmer, in their own
  language.
- Adding another report language later needs no structural change.

---

## D004 — Safety violations always downgrade to APPROVAL; there is no "drop" outcome

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** Rule 3 says that any action exceeding a safety limit is
downgraded to APPROVAL and is never silently dropped or executed. The demo,
however, describes a "rain-blocked irrigation", and the emergency stop must
block every action.

**Decision.**
- The gate has only three outcomes: `EXECUTE`, `EXECUTE_AND_NOTIFY` and
  `AWAIT_APPROVAL`. Every rule violation, including rain forecast and the
  emergency stop, produces `AWAIT_APPROVAL`. The task records the rule and
  the reason.
- In the demo, "rain-blocked" means that autonomous execution was blocked.
  The irrigation waits as a pending approval that shows the rain rule.
- The farmer-facing UI never uses the word "blocked". A downgraded task is
  labelled with the rule that caused it. For rain, the label is
  "Pendiente de aprobación por lluvia prevista" ("Pending approval: rain
  forecast"). This makes clear that the agent applied a rule and did not
  fail.
- While the emergency stop is active, approving a task returns 409 and the
  task stays pending. The actuator also refuses to execute anything.
- An explicit approval is a conscious override by the farmer of the limits
  shown on the approval card. Approval re-checks only the emergency stop.

**Consequences.**
- No proposal is ever lost.
- The farmer keeps the final say over quantitative limits, such as the 25 mm
  example in the README.
- Nothing can bypass the emergency stop.

---

## D005 — Mandatory-approval action types are enforced in config and verified at startup

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** Rule 5 puts the default levels in `config/autonomy.yaml`. If
that file were edited by mistake, fertilizer could become autonomous.

**Decision.**
- The levels live only in `config/autonomy.yaml`.
- The loader holds a fixed set of mandatory-approval types: fertilizer,
  agrochemical, planting date change, harvest timing, product listing, price
  change and chemical injection.
- The app refuses to start if any of these types is not set to `approval`.
- Approved fertilizer and agrochemical tasks become manual tasks for the
  farmer. The actuator never runs them.
- `CHEMICAL_INJECTION` exists in the enum but has no actuator command.
  Approving it returns 422 (not supported) and logs the attempt.

**Consequences.**
- Moving these types to a weaker level would need a change in two places,
  one of them in code. That makes an accidental weakening unlikely.
- **Required test:** loading an `autonomy.yaml` that sets any
  mandatory-approval type below `approval` must raise, and `create_app()`
  must refuse to start. There is one parametrized case per mandatory type.

---

## D006 — Stage autonomy mapping can only make the level stricter

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** The crop catalog has a per-stage autonomy mapping, and
`autonomy.yaml` has per-action defaults. The brief does not say which one
wins when they differ.

**Decision.** The effective requested level is the stricter of the two:
`strictest(default_level, stage_level)`. The order of strictness is
`APPROVAL > NOTIFY > AUTONOMOUS`.

**Consequences.**
- Crop data cannot relax a safety-relevant default.
- **Required test:** a stage mapping that tries to relax a level, such as
  `stage_level=AUTONOMOUS` with a default of `NOTIFY`, must produce the
  stricter level. The tests cover every pair of levels.

---

## D007 — NOTIFY revert semantics

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** A NOTIFY action executes immediately but must be revertible
within a window. Irrigation water that has already been applied cannot be
removed.

**Decision.**
- The revert window is `revert_window_seconds` in `autonomy.yaml` (default
  21600, which is 6 h; see D010 for the demo override). It is measured on
  the injected simulation clock.
- **Executing** a NOTIFY task means committing it: the task enters the
  calendar as `SCHEDULED` or runs right away.
- **Reverting** within the window works as follows:
  - A scheduled task that has not run is cancelled.
  - A calendar shift is moved back to its original date.
  - An irrigation that is still running is stopped. The volume already
    applied is recorded in the event log.
- A revert after the window, or of a fully applied irrigation, returns 409.
  The refused attempt is logged with its reason.
- Every revert event, whether successful or refused, records the amount of
  water actually applied before the revert:
  - `applied_mm` and `requested_mm`;
  - `applied_liters`, computed as `applied_mm × zone area in m²`, since
    1 mm on 1 m² is 1 L.

**Consequences.**
- The revert button is honest: it never claims to undo something that
  cannot be undone.
- The water balance in the event log always matches what reached the
  field.

---

## D008 — Add `POST /tasks/{id}/reject`

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** The brief lists an approve endpoint but no reject endpoint.
Without one, the farmer could only ignore a pending task.

**Decision.** Add `POST /tasks/{id}/reject` with an optional reason. It sets
the task to `REJECTED` and logs a `rejection` event.

**Consequences.**
- Every pending approval has an explicit end state.
- The event log records the farmer's "no" as clearly as a "yes".

---

## D009 — Demo: the extra irrigation is scheduled for the next day

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** The demo irrigates 15 mm, then proposes an extra 10 mm as a
NOTIFY action. On the same day the total is 25 mm. That exceeds the 20 mm
daily cap and the 12 h minimum interval, so the action would be downgraded
to APPROVAL (D004), and the NOTIFY revert step could not be shown.

**Decision.**
- The extra irrigation is scheduled for the next simulated day, at least
  12 h after the first irrigation. It stays within every limit and keeps its
  NOTIFY level.
- The task is committed as `SCHEDULED` and reverted before its
  `scheduled_for`.

**Consequences.**
- **Required test (end-to-end):**
  - The extra irrigation stays `SCHEDULED` while the accelerated clock is
    before `scheduled_for`.
  - The revert happens in that state.
  - No `execution` event exists for the task.
  - The daily total for the first day stays at 15 mm.
- The demo never shows the agent breaking its own rules.

---

## D010 — Revert window in seconds, with a demo-only override

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27) · Amended by D011 (2026-10-27)

**Context.** The default 6 h window is too long to show live. A shorter
window should not leak into normal operation by accident.

**Decision.**
- `config/autonomy.yaml` stores `revert_window_seconds` (default 21600).
  This stays the single source of the default.
- The environment variable `DEMO_REVERT_WINDOW_SECONDS` can override it,
  but only when `APP_PROFILE=demo`. In any other profile, setting the
  variable stops the app at startup.
- The override must be a positive integer.
- When the override is active, the app writes a startup event to the event
  log with the configured value and the override value.

**Consequences.**
- The demo can show a window that expires within seconds of simulated time.
- A production run cannot silently use a shortened window.
- Because the window is measured on the simulated clock (D007), the clock's
  speed factor also shortens it in real time.
- *Corrected by D011.* The override shortens the window in simulated time.
  It does not make the window run while the clock is paused: a paused clock
  means a paused window. To show the expiry in the demo, resume the clock.
  The original text said the override was for showing an expiry while the
  clock is paused, which contradicts D007.

---

## D011 — Revert countdown in the UI: the backend decides, the UI only displays

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** The revert window is measured on the simulated clock (D007).
When that clock is paused, a frozen countdown can look like a broken revert
to the jury. A second, wall-clock countdown that reached zero while the
backend still accepted the revert would be an actual contradiction.

**Decision.**
- The simulated clock is the only source of truth. The backend sends
  `revert_deadline` (simulated time) and `revert_open` (boolean) with every
  revertible task.
- The UI never computes expiry. It only displays what the backend sends,
  and it enables or disables the revert button only from `revert_open`.
- The revert card is labelled "Ventana en reloj simulado". It shows the
  remaining simulated time and a decorative real-time estimate
  (remaining ÷ speed factor, e.g. "≈ 52 s reales a ×360"), marked in the UI
  as an estimate.
- While the clock is paused, the counter is frozen and the card says
  "Reloj simulado en pausa: la ventana no avanza".
- After expiry, the card says "Ventana cerrada" and the revert button is
  disabled with the reason visible.
- In the demo, the expiry is shown by resuming or speeding up the clock.

**Consequences.**
- There is one clock, and tests stay deterministic.
- The displayed estimate can never contradict the backend, because it
  decides nothing.
- **Required test:**
  - With the simulated clock paused before `revert_deadline`, a revert is
    accepted no matter how much wall-clock time has passed.
  - After resuming the clock past `revert_deadline`, a revert returns 409.

---

## D012 — Schema built with `create_all`; no migrations during the hackathon

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** Migrations (Alembic) cost setup time, and the data model will
still change during the hackathon.

**Decision.**
- The schema is created with `SQLModel.metadata.create_all`.
- **The schema is reset on every schema change.** Existing databases are not
  upgraded. `create_all` does not alter existing tables, so an old
  `fieldpilot.db` must be deleted.
- The demo database is always regenerated with `make seed` (build step 11).
- No data is expected to survive between versions.

**Consequences.**
- There is no migration code to maintain while the model changes.
- Anyone who tries to keep data between versions will lose it. This entry
  documents that, so it is no surprise.
- A real deployment would introduce migrations before storing any farm data.

---

## D013 — Idempotency keys on execution requests; reconciliation by key

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** Physical execution happens between two database transactions
(write-ahead, see `architecture.md` §4.3). A crash between them leaves an
`execution_requested` event without a closing event. Restarting must never
water twice.

**Decision.**
- Every `execution_requested` event carries an idempotency key of the form
  `task-{id}:attempt-{n}`. The event log enforces it: the event is rejected
  without a key, and `(kind, idempotency_key)` is unique.
- An execution request is closed by an `execution` or `execution_failed`
  event with the same key. Other event kinds never close it.
- At startup, reconciliation decides by key:
  - If the actuator has a record of that key, the command was applied. The
    service writes the closing event with the recorded result and does not
    retry.
  - If the actuator has no record, the task moves to `FAILED`, the farmer
    is notified, and nothing is retried automatically. A late irrigation
    needs a new decision. This is the safer option.

**Consequences.**
- A restart never re-irrigates.
- Every interrupted action ends in an explicit, explained state.
- Step 2 provides the key, the uniqueness constraint and
  `find_unclosed_execution_requests()`, with tests. The reconciliation
  service and `Actuator.lookup` come in step 6.

---

## D014 — Simulator state lives in memory; what the user sees after a restart

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** Persisting the full simulator state (water balance, active
scenarios, valve runs) would add schema and code that only the demo needs.

**Decision.**
- Soil moisture is rebuilt at startup from the latest stored `Reading` of
  each zone.
- Active scenarios and valve runs live only in memory and are lost on
  restart. Nothing resumes on its own.
- An irrigation interrupted by a restart is closed by D013 reconciliation.
- **The UI shows active scenarios only from the simulator**
  (`FieldSimulator.active_scenarios(now)`), never from a stored copy or the
  event log.
- After a restart during a drought, the UI shows no active scenario,
  because none is being applied. The event log still shows the earlier
  `scenario_injected` event and its window.
- When a `scenario_injected` window that is still open in the log has no
  matching active scenario in the simulator, the UI shows a notice:
  "El simulador se reinició; el escenario «sequía» ya no se está aplicando".
  It never shows "sequía" as if it were still active.

**Consequences.**
- The UI can never claim an effect the simulator is not applying.
- Re-injecting the scenario is an explicit, logged action.

---

## D015 — Soil moisture units: volumetric content vs. percent of field capacity

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** Sensors report volumetric water content (%). The safety limit
"do not irrigate above 85 %" is relative to field capacity. Comparing a raw
reading of, say, 30 % with the 85 % limit would never trigger the rule.

**Decision.**
- Readings are stored as volumetric content (`soil_moisture_vwc`).
- Rules use the percent of field capacity, computed only by
  `domain/units.pct_of_field_capacity(vwc, field_capacity_vwc)`.
- `ZoneSnapshot` carries both values, and so does the UI.

**Consequences.** A single conversion point removes a whole class of unit
errors.

---

## D016 — The demo moves time with controlled `advance()`

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** Two goals pull in different directions. The NOTIFY extra
irrigation for the next day (D009) must be reverted before it runs. The
revert window, measured on the simulated clock, must be visibly open or
closed.

**Decision.**
- The demo and the end-to-end test keep the clock paused and move time with
  explicit `ClockService.advance()` calls. These are deterministic and
  logged as `clock_changed`.
- `advance()` only moves the clock. The simulator integrates every skipped
  15-minute substep on its next `advance_to`, so no physics is skipped.
  The revert window is a deadline comparison and needs no substeps.

**Consequences.**
- **Required test (step 11):** after the NOTIFY task is created, advancing
  by less than the revert window lets the revert succeed, and advancing
  past it makes the revert fail with 409.
- **Required test (step 11):** the task stays `SCHEDULED` until an
  `advance()` crosses `scheduled_for`, with no `execution` event before
  then (D009).

---

## D017 — Agronomic sources for the maize catalog, verified before commit

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27). Citation and GDD method amended by D031.

**Context.** The first proposal cited degree-days and Kc values from memory.
Those values had to be checked against their sources before the catalog
was committed.

**Decision.**
- Every numeric field in `config/crops/*.yaml` names a source declared in
  the same file, with its citation, URL, verification status and
  verification date. The loader rejects any field without a known source.
- **Degree-days:** cumulative GDD from Abendroth et al. (2011), PMR 1009,
  as tabulated in Ohio State AGF-0101 Table 1. The values are in °F·day
  with the Modified 86/50 °F method and were converted by dividing by 1.8.
  The rows used, verified on 2026-10-27, are:
  - VE: 100 °F·day → 55.6 °C·day
  - VT/R1: 1420 → 788.9
  - R2: 1686 → 936.7
  - R5: 2324 → 1291.1
  - R6: 2650 → 1472.2
- **Kc:** FAO-56 Table 12, "Maize, Field (grain)". Kc mid 1.20 and Kc end
  0.60 were verified. Kc ini 0.30 is **partially verified**: it is read
  from the cereals group value, and the online table layout was garbled.
- **Values without an agronomic source** are marked as such. Moisture
  targets and nutrient amounts are `demo_value`. The 20 °C·day start of
  germination is a `project_convention`, because the sources define no
  boundary between sowing and germination.
- The catalog declares `reviewed_by_agronomist: false`. Tests check that
  it is not presented as reviewed and that demo values are never labelled
  verified.

**Correction recorded for transparency.** The values first proposed from
memory were wrong. For example, flowering was set at 700 °C·day, while the
source gives 788.9. Verification caught this before the commit, and tests
now pin every threshold to its published value.

**Consequences.**
- Every number can be traced to its origin.
- Before the demo, a team member should re-read the source pages linked in
  the YAML to confirm them.

---

## D018 — The phenology day is the plot's local calendar day

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** The daily minimum and maximum temperature define each day's
GDD. In Neiva (UTC−5), the UTC day ends at 19:00 local time, so a UTC day
would mix two different nights.

**Decision.**
- `Plot.utc_offset_hours` is required, with no default, so a plot can
  never silently fall back to UTC.
- A day's readings are those in `[local midnight, next local midnight)`,
  computed by `local_day_window`.
- A day is processed only after it has ended in simulated time.

**Consequences.** A test places a minimum at 22:00 local time, which is the
next day in UTC, and checks that it is counted in its local day.

---

## D019 — Phenology never invents data; gaps are recorded, not filled

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** A day can have no temperature readings, for example because a
sensor was down. Filling the day from the forecast or from averages would
move stages and the calendar on data that was never measured.

**Decision.**
- A day without readings raises `MissingDataError` and writes nothing.
- The next day with data counts **only its own GDD**. The skipped days are
  logged in one `phenology_gap` event, which says their degree-days were
  not counted and stage dates may lag.
- Data that arrives later for a gap day is not back-filled. Days are
  counted once, in order, so totals never change after the fact.
- Processing is idempotent: a day at or before `gdd_updated_through`
  changes nothing.

**Consequences.**
- Stage estimates err on the late side after a gap, and the reason is
  visible in the event log.
- Tests cover the failing day, the following day and a late arrival.

---

## D020 — The maize catalog is a reference that must be calibrated locally

- **Date:** 2026-10-27
- **Status:** Accepted (2026-10-27)

**Context.** The degree-days come from US Corn Belt hybrids, and the FAO-56
Kc values assume standard conditions: a subhumid climate, RHmin of about
45 % and wind of about 2 m/s. The target region, Neiva in Huila (about
430 m, a warm climate), differs on both counts.

**Decision.**
- **The catalog values are a reference that must be calibrated with local
  data before any real use.** That applies to hybrid-specific GDD, local
  Kc and local agronomic advice on moisture and nutrients.
- This limitation is stated in the YAML (`calibration_note`), in the
  README and here.
- The architecture already allows calibration: a calibrated crop is a new
  YAML file with its own sources, and no code changes.

**Consequences.**
- The demo shows the mechanism, and the jury can see exactly which numbers
  would change in the field.
- As a rough check, a typical Neiva day (22/34 °C) gives 16 °C·day, so
  maturity takes about 92 days. That is plausible for a warm lowland site,
  but it is not a validated prediction.

---

## D021 — FAO-56 Kc ini (0.30) stays "partially verified" until checked in the original table

- **Date:** 2026-10-27
- **Status:** Superseded by D031

**Context.** A reviewer reading the full FAO-56 Table 12 must not find a
gap between the catalog and the source. A second check on 2026-10-27
confirmed two things. The "Maize, Field (grain)" row has no Kc ini of its
own, and FAO-56 states that a group's single Kc ini value represents the
whole group. The cereals group header reads 0.3 in the online text, but
that column may be rendered from an image, so the value was not confirmed
against the original table.

**Options considered.**
1. Confirm 0.30 against the complete source.
2. Replace it with a value verified for the sowing stage.
3. Keep it and say explicitly that it is partially verified.

**Decision.** Option 3, until a person checks the original:
- The YAML keeps `verification: partially_verified`, with a note that
  explains the inheritance and the uncertainty.
- The README says, in its own bullet, that Kc ini is only partially
  verified.
- No other verified value replaces it. No sowing-stage Kc was found in a
  verified source, and Kc ini depends on wetting frequency: FAO-56 gives a
  range of 0.1 to 1.15.

**How to close it.** Open FAO-56 Table 12 in the original publication (the
PDF or the printed paper) and read the cereals group Kc ini.
- If it is 0.3, set `verification: verified` and a new `verified_on`, and
  update this entry to Option 1.
- If it differs, change the value; the catalog test will show the change.

**Consequences.** The only partially verified number is labelled as such in
every place a reviewer would look.

---

## D022 — Emergency stop: what it blocks and what it never blocks

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** The brief says that while the emergency stop is active, the
gate returns APPROVAL with an `emergency_stop_active` violation. Applied
literally to every action, that blocks two things that must keep working
in an emergency:

- closing a valve, which reduces the risk;
- telling the farmer that the crop is under stress.

**Decision.**
- **The emergency stop blocks every action that adds water or changes the
  plan.** That is every action type except the informational ones,
  `stress_alert` and `stage_report`, which change nothing physical or
  planned. Those are outside the rule's scope; this is not an exemption.
  They keep their normal level (`stress_alert` stays autonomous), so the
  farmer does not lose information when they need it most.
- **The only exemption is `stop_irrigation`.** It is a valve command and
  so inside the scope, but closing a valve can only reduce risk.
- The scope (informational types) and the exemption list
  (`stop_irrigation`) are two fixed sets in code. Both are tested.
- **The emergency stop is evaluated before every other rule.** For a
  blocked type, the verdict's `reason_code` is always
  `emergency_stop_active`, even when other rules or the always-approval
  list also apply. The other violations are still listed. The farmer and
  the jury therefore see the exact cause, rendered from the message
  catalog, and never a generic text.
- Approval while the stop is active returns 409 (D004, step 9). The
  actuator also refuses to execute (defense in depth, step 6).

**In one sentence, for the demo:** the emergency stop *blocks everything
that adds water or changes the plan, and still lets you close valves and
see alerts.*

**Consequences.**
- The exemption list has a single entry.
- Any new action type is blocked by default unless it is classified as
  informational. Adding a type to either set needs a new decision entry,
  so the demo sentence stays true.

---

## D023 — The proposal key is derived from the proposal's content

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** `UNIQUE(kind, idempotency_key)` stops a second `gate_verdict`
with the same key. If each attempt carried a fresh UUID, an agent that
retries the same proposal would get two verdicts, and possibly two
irrigations. The constraint would then protect only against resending the
same object, not against agent retries.

**Decision.**
- `proposal_key = "proposal-" + sha256(canonical JSON of {action_type,
  plot_id, zone_id, local day of scheduled_for, params})`.
- Canonical JSON means sorted keys and floats rounded to 3 decimals, so
  `15` and `15.0` give the same key.
- **Excluded from the key:** `rationale`, `estimated_cost` and
  `proposed_by`. They vary between LLM attempts without changing what
  would happen in the field.
- The key is computed by one pure function in the domain. Callers never
  build keys themselves.
- A second proposal with the same key creates no new verdict: the service
  returns the existing one.
- Proposal keys (`proposal-…`) and execution keys (`task-{id}:attempt-{n}`,
  D013) live in different namespaces and never collide.

**Consequences.**
- An agent retry within the same local day is recognized as the same
  proposal.
- A truly different proposal still gets its own verdict: another volume,
  zone or day.
- Re-proposing the same action on the same day after the farmer rejected
  it returns the earlier verdict instead of creating a new pending task.
  That is accepted: the farmer already answered.
- **That reuse must be visible.** `record_verdict` returns the verdict
  together with `already_decided_at` (the time of the original decision,
  or `None` for a new one). The agent's reply and the UI show the earlier
  verdict with the label "Ya decidida el {fecha}", taken from the message
  catalog, so the system never looks as if it ignored the request.

---

## D024 — `harvest_timing` is the action type name, not `harvest_timing_change`

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** The step 5 brief lists the always-approval type as
`harvest_timing_change`. The `ActionType` enum, defined in step 2, calls
it `harvest_timing`.

**Decision.**
- The config and the code use `harvest_timing`.
- Using the brief's name would create a key that matches no action type.
  D005 would then protect nothing, with no visible error.

**Consequences.** Unknown action types in `autonomy.yaml` stop the app, so
this kind of mismatch can never pass silently in the future.

---

## D025 — Every action type must have an explicit level

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** The brief's default list does not include `stop_irrigation`.

**Decision.**
- `autonomy.yaml` must give a level to every `ActionType`. A missing type
  stops the app; nothing falls back to a silent default.
- `stop_irrigation` is `autonomous`, as stated in the README.

**Consequences.** Adding a new action type forces a deliberate choice of
level before the app can start.

---

## D026 — The calendar-shift limit lives in `safety.yaml`

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** The brief's `safety.yaml` keys do not include the 2-day
calendar limit (non-negotiable rule 3).

**Decision.**
- Add `max_calendar_shift_days: 2` to `safety.yaml`.
- The rule applies to `calendar_shift`, `planting_date_change` and
  `harvest_timing`, using `abs(params.shift_days)`, so moving a task
  earlier counts the same as moving it later.

**Consequences.**
- **Required test:** a 2-day shift passes and a 3-day shift goes to
  APPROVAL, in both directions.
- A missing `shift_days` is `missing_input` (D027).

---

## D027 — Missing input to a safety rule is a violation

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** A rule can lack the data it needs: no forecast, no moisture
reading, no field capacity, or no `volume_mm` / `shift_days`.

**Decision.** A missing input produces a `missing_input` violation that
names the input, so the action goes to APPROVAL. A rule never assumes it is
satisfied. This is the same principle as D019.

**Consequences.** A sensor or forecast outage moves irrigation to the
farmer's approval queue instead of watering blind.

---

## D028 — Step 5 commit order and staged-only verification

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** The proposed order put `chore(config)` after
`feat(autonomy)`. The gate and startup tests load the real YAML files, so
that commit would fail `make check`. Also, `make check` on the working
tree does not prove that the *staged* commit passes.

**Decision.**
- The commit order is: docs → `feat(safety)` → `chore(config)` →
  `feat(autonomy)`.
- A commit that touches only documentation (`.md`) runs `make check`
  directly; there is no uncommitted code that could hide a failure.
- From the second commit on, when uncommitted code exists, check only what
  is staged:

  ```bash
  git stash push --keep-index --include-untracked -m pre-commit-check
  make check; status=$?
  git stash pop
  git stash list      # must be empty
  ```

  The `;` makes sure the `pop` runs even when `make check` fails. Commit
  only if `status` was 0.

**Consequences.** Every commit on the branch passes `make check` on its
own.

---

## D029 — Mandatory-approval tests use a list independent of the code

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** The D005 startup tests were first parametrized from the
`MANDATORY_APPROVAL` constant they guard. A mutation check showed that
removing `fertilizer` from the constant made its tests disappear instead
of fail (474 → 470 tests, all green).

**Decision.**
- Mandatory-approval tests are parametrized from `BRIEF_ALWAYS_APPROVAL`
  in `tests/builders.py`, a list written independently of
  `MANDATORY_APPROVAL`.
- A guard test asserts that both are equal. Changing either alone fails
  CI; parametrizing from the constant would let a dropped type silently
  lose its tests.
- A type listed in `always_approval` in `autonomy.yaml` beyond the
  mandatory set must also default to approval, or the app refuses to
  start.

**Consequences.** Adding a mandatory type takes two edits, the constant
and the test list, and CI shows the change.

---

## D030 — The Kc curve is a list of points, independent of the stages

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28)

**Context.** Each stage carried its own Kc, so the Kc curve could only bend
at stage boundaries. The mid-season plateau (Kc 1.20) began at flowering
(788.9 °C·day). FAO-56 starts it at effective full cover, which for maize
comes earlier, so the model underestimated ET in the weeks before
flowering, the most water-sensitive window.

FAO-56 defines the stages by ground cover and maturity, not by leaf stage:
- initial: from planting to approximately 10 % ground cover;
- development: to effective full cover;
- mid-season: from effective full cover to the start of maturity;
- late season: from the start of maturity to harvest.

FAO-56 adds that "effective full cover for many crops occurs at the
initiation of flowering", but for row crops such as maize it defines it as
"the time when some leaves of plants in adjacent rows begin to
intermingle", that is, canopy closure, which comes before flowering and
depends on row spacing.

**Decision.**
- Kc is a crop-level curve of points (`kc_curve`), interpolated linearly.
  Stages keep moisture targets, nutrients and autonomy only.
- No source maps the FAO-56 points to leaf stages, so the mapping is a
  project convention (source `kc_stage_mapping`). The degree-day values
  come from AGF-0101 Table 1:
  - end of initial: V3, 346 °F·day → 192.2 °C·day (V3–V6 is plausible);
  - effective full cover: V12, 1020 → 566.7 (V12–V15 is plausible);
  - start of maturity, where Kc starts to fall: R5 (dent), 2324 → 1291.1.
- The last point is R6 (black layer, 1472.2 °C·day), the catalog's
  `maturity_gdd`, with Kc end 0.60 from FAO-56 Table 12 note 11 (harvest
  at high grain moisture). AGF-0101 gives kernel moisture at R6 as
  averaging 30 % (25–40 %), consistent with that note.
- Where the window is uncertain, the earlier point was chosen.

**Cost of the decision.** The model overestimates ET between V3 and V6 and
between V12 and V15. In those windows irrigation applies more water than
the crop needs, with a risk of nitrate leaching and of wasted water and
energy. The 20 mm/day cap (D001) bounds that effect in the demo.

**Consequences.**
- Flowering (788.9) now falls inside the 1.20 plateau.
- `crop_coefficient_at` keeps its signature, so the simulator does not
  change.
- Both mapped points must be confirmed with local field observations (row
  spacing, hybrid) before real use (D020).

---

## D031 — Phenology source review: citation, GDD method and Kc ini

- **Date:** 2026-10-28
- **Status:** Accepted (2026-10-28). Supersedes D021; amends D017.

**Context.** A second review of the maize catalog against its sources found
four things to correct.

**Decision.**
- **Citation.** AGF-0101, "Corn growing degree days: A method of maturity
  rating for hybrids", by Eckert & Thomison (2017), revised by Ortez &
  Lindsey (2023). Its Table 1 footnote says the cumulative GDD are adapted
  from Abendroth et al. (2011), PMR 1009, and from Nielsen, R.L. (2021),
  "Grain Fill Stages in Corn", Purdue University. Nielsen is now cited.
- **GDD method.** Purdue AY-312-W caps the daily high at 86 °F (30 °C) and
  raises the daily low to 50 °F (10 °C); it does not cap the low at 30 °C.
  `daily_gdd` now follows that form:
  `max(0, (min(high, 30) + max(low, 10)) / 2 − 10)`. The old code clamped
  both values to [10, 30], which differs only on nights above 30 °C.
- **Kc ini.** `fao56_kc_ini = 0.30` is verified against the online edition
  of FAO-56 Table 12: the cereals group row, with the Kc ini column
  confirmed by its alignment with Kc mid and Kc end and by the
  group-inheritance rule in the chapter text. The original PDF was not
  checked. Kc ini depends on wetting frequency (FAO-56 Table 12 note 1,
  Figs. 29–30); the sowing value is documented as a planning value.
- **Calibration path.** The calibration note names the concrete method:
  FAO-56 Equations 62 and 65 adjust Kc mid and Kc end when RHmin differs
  from 45 % or wind speed from 2 m/s.
- **Stage name.** The stage that ends at VE is shown as "Germinación
  (hasta la emergencia)" / "Germination (to emergence)", because
  emergence is its end, not part of it. The internal key
  `germination_emergence` does not change.

**Consequences.** A test pins the 32 °C night case (21 °C·day, not 20).
The README no longer lists Kc ini as partially verified.

---

## D032 — An irrigation cut by a restart is reported as of unknown size

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** D013 closes execution requests left open by a crash. It does
not cover an irrigation that was already `EXECUTED` and still running when
the process restarted. That task has no open request, and its valve run is
lost with the simulator's memory (D014). D014 says D013 closes it, but D013
cannot see it.

**Options considered.**
1. Report it, with the applied amount unknown.
2. Estimate `applied_mm = rate × (sim time at startup − start)`.
3. Add an `execution_interrupted` event kind.

**Decision.** Option 1.
- At startup, reconciliation flags every `EXECUTED` irrigation that meets
  both conditions:
  - its natural end is after the last event logged before startup, which
    is the last moment the backend is known to have run;
  - the actuator does not know its key.
- For each flagged irrigation, reconciliation:
  - sends `close` to that zone's valve, which is always allowed, in case
    real hardware kept running;
  - writes one `notification` event with `requested_mm`,
    `applied_mm: null` and the reason. Its key is
    `interrupted:{execution key}`, so a second restart does not repeat it;
  - creates a Notification for the farmer.
- **The farmer's message says that the irrigation may have continued
  after the restart and that the amount applied is unknown.** A bare
  "riego cerrado" would leave the farmer not knowing how much water the
  crop received.
- The task stays `EXECUTED` and is never reopened.
- The daily cap counts it by the millimetres requested, which is the
  conservative reading (D035).

**Why not the others.** Option 2 invents a number. If the clock was running
during the outage, wall time inflates the estimate. Option 3 adds an event
kind where `notification` is enough.

**Consequences.** No irrigation of unknown size is hidden, and none is
counted as smaller than it may have been.

---

## D033 — A scheduled task is re-evaluated when its time comes

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** A `SCHEDULED` task, such as the next-day extra irrigation of
D009, runs hours after its verdict. Rain, the emergency stop or another
irrigation may have changed the picture since then. Permits also live in
memory and do not survive a restart.

**Options considered.**
1. Re-evaluate with a fresh context.
2. Keep the original verdict and re-check only the emergency stop.
3. Add a `SCHEDULED → PENDING_APPROVAL` transition.

**Decision.** Option 1.
- `DueTaskRunner.run_due(now)` is called explicitly (D016). For each due
  task the actuator supports, it rebuilds the action, gets a fresh context
  and calls `gate.authorize`.
- **With a permit**, the task runs through the write-ahead protocol. The
  fresh verdict is stored in the `execution_requested` inputs. It is not a
  second `gate_verdict`, which is unique per proposal key.
- **Without a permit**, the task moves to `FAILED` with an
  `execution_failed` event. That event carries the verdict, its reason
  code and every violation, and the actuator is never called.
- **The farmer saw this task as scheduled, so the notification names the
  rule that changed**, rendered from the message catalog as in D004. For
  example: "La tarea programada no se ejecutó: pendiente de aprobación por
  lluvia prevista (8 mm > 5 mm). Requiere una nueva decisión."
- A new decision needs a new proposal.

**Consequences.** Nothing runs on a stale verdict, and a downgrade is never
silent. The task lifecycle does not change.

---

## D034 — `calendar_shift` execution waits for the calendar (step 7)

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** D007 says that reverting a calendar shift moves the task back
to its original date. No calendar exists to move yet; it comes with the
planner in step 7.

**Decision.**
- In step 6, a `calendar_shift` task can be created, and reverted while it
  is `SCHEDULED`.
- The actuator raises `UnsupportedActionError` for it, and
  `DueTaskRunner` leaves it scheduled.
- Its execution, and its revert after execution, are built in step 7.

**Consequences.** Step 6 never claims to move a date it cannot move.

---

## D035 — What the gate counts toward the daily cap and the interval

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29). Amended by D040.

**Context.** The safety context must be built from stored facts, never
supplied by the caller. Otherwise the agent could under-report water. The
brief does not say which irrigations count.

**Decision.**
- `StoredGateContextProvider` builds the context per zone and per local
  day of the plot (D018).
- For the daily cap and the 12 h interval it counts:
  - executed irrigations, by the millimetres applied;
  - scheduled irrigations, by the millimetres requested, so two scheduled
    15 mm irrigations cannot each pass on their own;
  - interrupted irrigations, by the millimetres requested (D032).
- Reverted and failed tasks do not count.
- The rain forecast comes through a `RainForecast` port. Tests use a
  fake; the Open-Meteo adapter comes in step 8. Until then a missing
  forecast is a violation (D027).

**Consequences.** The cap holds across tasks that are committed but not yet
run.

---

## D036 — The demo override can only shorten the revert window

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** D010 requires `DEMO_REVERT_WINDOW_SECONDS` to be a positive
integer. It does not say whether it may exceed `revert_window_seconds`.

**Decision.** An override larger than `revert_window_seconds` stops the
app at startup. The override exists to shorten the window for the demo,
not to lengthen it.

**Consequences.** The override cannot extend how long an action stays
revertible.

---

## D037 — Only the gate can issue an `ExecutionPermit`

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29). Mechanism amended by D039.

**Context.** The brief requires that the actuator can never be called with
a raw action. The architecture allows only the gate to authorize an
execution.

**Decision.**
- `AutonomyGate.authorize(action, context)` returns the verdict and,
  only for `EXECUTE` or `EXECUTE_AND_NOTIFY`, an `ExecutionPermit`.
- The permit carries a token private to `gate.py`. Building one anywhere
  else raises `PermissionError`.
- `Actuator.execute` checks the token, and checks that the permit matches
  the task (type, zone and parameters).
- `evaluate` stays pure and unchanged.
- The approval path of step 9 will add its own gate method, so an
  approved task also receives a gate-issued permit.

**Consequences.** Python cannot make construction strictly impossible, but
bypassing the token takes a deliberate import of a private name. A test
pins the refusal.

---

## D038 — One irrigation rate for every simulated valve

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** `ValveController.open` needs a flow rate. Neither zones nor
proposals carry one, and the agent should not choose it.

**Decision.**
- `config/actuation.yaml` holds `irrigation_rate_mm_per_h: 6.0`, marked
  as a demo value.
- The actuator uses it for every opening and records it in the result.

**Consequences.** Closing mid-irrigation applies `rate × elapsed`, capped
at the target, on a known rate. A per-zone rate can come with real
hardware.

---

## D039 — The permit is unforgeable through its constructor, not a token

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29). Amends the mechanism of D037.

**Context.** D037 put a private token in a field of the permit. During
implementation this turned out to have a hole: `dataclasses.replace(permit,
zone_id=3)` copies the token, so a valid permit could be re-aimed at
another zone without the gate.

**Decision.**
- `ExecutionPermit.__init__` always raises `PermissionError`. Because
  `dataclasses.replace` calls the constructor, it raises too.
- Only `_issue_permit`, private to `gate.py`, builds a permit, and only
  `AutonomyGate.authorize` calls it.
- `Actuator.execute` refuses anything that is not an `ExecutionPermit`,
  and still checks that the permit matches the task.

**Consequences.**
- Forging a permit now takes a deliberate `object.__new__` on a private
  type.
- Tests pin that a permit cannot be built by hand or copied with changes.

---

## D040 — A reverted irrigation counts the water it applied

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29). Amends D035.

**Context.** D035 said reverted tasks do not count toward the daily cap.
That holds for a task cancelled while `SCHEDULED`, which applied nothing.
It does not hold for an irrigation stopped mid-run: in the step 6 test it
had applied 9 mm of a requested 10 mm. Counting it as 0 would let the next
proposal exceed the 20 mm cap.

**Decision.**
- A reverted irrigation counts the `applied_mm` recorded on its `revert`
  event. That value is 0 for a scheduled task that was cancelled.
- Failed, rejected and pending tasks still count nothing.

**Consequences.** The cap reflects the water that reached the field. A test
pins that a run stopped at 9 mm counts 9 mm, neither 0 nor the 10
requested.

---

## D041 — CI runs the same Makefile targets as local development

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** Until now `make check` was the only gate, run by hand before
each commit (D028). The repository needs the same gate on every pull
request, without a second definition of "passing" that could drift from
the local one.

**Decision.**
- `.github/workflows/ci.yml` runs on pull requests to `main`, on pushes to
  `main`, and on demand. It has three jobs, whose names are the
  required status checks:
  - **Repository hygiene:** `make check-repo` fails if a `.env` file
    (other than `.env.example`) or a database file is tracked (rule 7).
  - **Backend:** `make install-backend` (`uv sync --locked`, so a stale
    `uv.lock` fails), `lint-backend`, `typecheck-backend` and `test`.
    Then it checks that the tests left the working tree clean, so no
    test can write a database into the repository.
  - **Frontend:** `make install-frontend` (`npm ci`) and
    `check-frontend` (`tsc` and `vite build`).
- `make check` is now `check-repo`, `check-backend` and `check-frontend`.
  Locally it also builds the frontend, as CI does.
- **No secrets.** The workflow uses no repository secrets.
  `MOCK_LLM=1` keeps the agent off the network, and the token is
  read-only (`contents: read`). Checkout does not keep credentials.
- **Pinned tools.**
  - Every action is pinned to a commit SHA, with its version in a
    comment. Dependabot proposes updates to the actions only, monthly.
  - uv is pinned to 0.12.3, the version used locally. Python comes from
    `backend/.python-version` (D002), and Node from `frontend/.nvmrc`
    (24).
- **Concurrency.** A newer push to the same pull request cancels the older
  run. Runs on `main` always finish.

**Consequences.**
- A pull request cannot be merged on a red check once the three checks
  are required in the branch ruleset.
- No Python or npm dependency was added. Dependabot covers GitHub Actions
  only, so dependency changes still go through an explicit commit
  (brief rule 9).

---

## D042 — Readability and cleanliness rules enforced in CI

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** CI ran ruff with the base rule set: errors, style, imports,
bugbear, pyupgrade, simplify, naming and ruff's own rules. Several project
principles, such as no `print`, aware UTC everywhere and small functions,
were enforced only by review.

**Decision.**
- **Rule families added**, each catching something a reviewer would
  otherwise have to flag:
  - `C90`, with complexity at most 10, and `PLR0911`/`PLR0912`/`PLR0915`:
    no function grows too many branches, returns or statements;
  - `ARG`: no unused arguments;
  - `RET`, `PIE`, `C4` and `PERF`: no needless code, ambiguous returns
    or hand-written loops a comprehension expresses better;
  - `ERA`: no commented-out code;
  - `T20`: no `print`, because the event log is the only channel
    (architecture §4.5);
  - `DTZ`: no naive datetimes (§4.10);
  - `SLF`: no access to another object's private members;
  - `PLE`/`PLW`/`PLC0415`: pylint errors and warnings, and imports at
    the top of the module;
  - `PTH`, `PT` and `TC`: pathlib, pytest conventions and typing-only
    imports;
  - `D100`: every application module has a docstring.
- **Not added**, because the churn would not buy readability:
  - full `D` (pydocstyle): 710 findings, mostly obvious one-line test
    functions;
  - `FBT`, `TRY` and `EM`;
  - `PLR2004` (magic values) and `PLR0913` (argument count): services
    take their dependencies through the constructor on purpose.
- **Ignored on purpose:** `PT018`, because a composite `assert a is not
  None and a.x == 1` narrows types for mypy.
- **Exceptions are explicit.**
  - Tests may keep unused arguments, because test doubles must match
    the protocol signatures they replace. They also need no module
    docstring.
  - Every other exception is an inline `noqa` with its reason: the
    shared `Rule` signature, SQLAlchemy's `TypeDecorator` signature,
    naive datetimes built on purpose to test their rejection, and the
    simulator's true water content, which has no public accessor.
- **CI** runs the rules and the formatting check as two separate steps.
  The rules step uses ruff's GitHub output, so every finding appears as
  an annotation on the exact line of the pull request.

**Consequences.**
- No dependency was added: every rule ships with ruff, which is already
  a dev dependency.
- Existing findings were fixed in the same change, for example an unused
  argument in `ExecutionService` and a loop rewritten as `extend`.

---

## D043 — Muse models through the official OpenAI Python SDK

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** The agent phase needs Muse Spark, SAM 3.1 and Muse Voice
Transcribe. The Meta workshop (`meta-models/legal-agent-workshop`) reaches
the Meta Model API with the official OpenAI Python SDK, using
`responses.create` against `https://api.meta.ai/v1`.

**Decision.**
- The `openai` package becomes a backend dependency, approved by Edwin on
  2026-10-29. The commit that adds it lists it and explains why (brief
  rule 9).
- `MuseClient` implements the `LLMClient` port with `responses.create`,
  `store=False` and `parallel_tool_calls=False`. The rest of the agent
  depends only on the port.
- **Model ids come from the environment:**
  - `MUSE_AGENT_MODEL=muse-spark-1.3`;
  - `MUSE_SEGMENTATION_MODEL=sam-3.1`;
  - `MUSE_TRANSCRIBE_MODEL=muse-voice-transcribe-1.0`.

  All three were confirmed with `GET /v1/models` on 2026-10-29.
- The variables keep the `MUSE_` prefix of `.env.example`, instead of the
  workshop's `MODEL_API_*`.
- `MOCK_LLM=1` remains the default and never reaches the network.

**Consequences.** The client can be swapped without touching the loop, the
tools or the subagents. Tests use `MockLLMClient` only.

---

## D044 — One loop engine; a fixed daily pipeline and an orchestrator for chat

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** The architecture plans four subagents (monitoring, irrigation,
imaging, reporting) and an orchestrator. The workshop teaches one agent in
one loop, where the model chooses every tool call. A model that also chose
the order of the subagents could route wrongly during the demo.

**Decision.**
- **One `AgentLoop`**, shared by every subagent. A subagent is a system
  prompt, a subset of tools and a closing tool.
- **Daily cycle:** Monitoring, Imaging, Irrigation, Reporting, in a fixed
  order. Inside each subagent, the model chooses every tool call.
- **Farmer chat:** the orchestrator is an agent whose tools consult the
  subagents and return their structured results.
- **Handoffs** are validated objects that cite observation ids (the
  `FieldBrief`), never free text.
- **Only Irrigation holds `propose_action`.** The other subagents have
  read-only tools.

**Consequences.** The demo is deterministic in its order and still agentic
in its decisions. A routing mistake can only happen in the chat, where the
gate still guards every action.

---

## D045 — The agent trace lives in the event log

- **Date:** 2026-10-29
- **Status:** Accepted (2026-10-29)

**Context.** The workshop saves progress every turn and shows it in a
console. FieldPilot already has an append-only event log and an
`agent_tool_call` event kind.

**Decision.**
- Every turn writes one `agent_tool_call` event. Its inputs hold the run
  id, the subagent, the turn, the tool, the arguments, the result or
  error, and the token usage.
- There is no new table: a run is the set of events that share its run id.
- API keys and environment values are never written to the trace.

**Consequences.** The dashboard draws the agent timeline from the event
log, so there is one audit trail for the agent and for the gate.
