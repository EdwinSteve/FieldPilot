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
- **Status:** Accepted (2026-10-27)

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
- **Status:** Accepted (2026-10-27)

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
