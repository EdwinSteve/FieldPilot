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
