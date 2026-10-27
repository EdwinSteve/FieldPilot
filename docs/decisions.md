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
