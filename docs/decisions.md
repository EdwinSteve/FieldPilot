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
- **Status:** Proposed

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
- **Status:** Proposed

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

**Consequences.** Moving these types to a weaker level would need a change in
two places, one of them in code. That makes an accidental weakening unlikely.

---

## D006 — Stage autonomy mapping can only make the level stricter

- **Date:** 2026-10-27
- **Status:** Proposed

**Context.** The crop catalog has a per-stage autonomy mapping, and
`autonomy.yaml` has per-action defaults. The brief does not say which one
wins when they differ.

**Decision.** The effective requested level is the stricter of the two:
`strictest(default_level, stage_level)`. The order of strictness is
`APPROVAL > NOTIFY > AUTONOMOUS`.

**Consequences.** Crop data cannot relax a safety-relevant default.

---

## D007 — NOTIFY revert semantics

- **Date:** 2026-10-27
- **Status:** Proposed

**Context.** A NOTIFY action executes immediately but must be revertible
within a window. Irrigation water that has already been applied cannot be
removed.

**Decision.**
- The revert window is `revert_window_hours` in `autonomy.yaml` (default 6).
  It is measured on the injected simulation clock.
- **Executing** a NOTIFY task means committing it: the task enters the
  calendar as `SCHEDULED` or runs right away.
- **Reverting** within the window works as follows:
  - A scheduled task that has not run is cancelled.
  - A calendar shift is moved back to its original date.
  - An irrigation that is still running is stopped. The volume already
    applied is recorded in the event log.
- A revert after the window, or of a fully applied irrigation, returns 409.
  The refused attempt is logged with its reason.

**Consequences.** The revert button is honest: it never claims to undo
something that cannot be undone.

---

## D008 — Add `POST /tasks/{id}/reject`

- **Date:** 2026-10-27
- **Status:** Proposed

**Context.** The brief lists an approve endpoint but no reject endpoint.
Without one, the farmer could only ignore a pending task.

**Decision.** Add `POST /tasks/{id}/reject` with an optional reason. It sets
the task to `REJECTED` and logs a `rejection` event.

**Consequences.**
- Every pending approval has an explicit end state.
- The event log records the farmer's "no" as clearly as a "yes".
