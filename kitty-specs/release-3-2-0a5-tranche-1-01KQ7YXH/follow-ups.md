# Follow-Ups: 3.2.0a5 Tranche 1

**Mission**: `release-3-2-0a5-tranche-1-01KQ7YXH`
**Generated post-merge**: 2026-04-27 (responds to `mission-review.md` PASS WITH NOTES)

This file captures the four LOW-severity findings from the mission review that are explicitly out of scope for the current tranche but should be addressed in future tranches.

---

## FU-1 — `--feature` alias has no deprecation warning (RISK-1)

**Source**: mission-review.md RISK-1
**Severity**: LOW
**Status**: by-design (C-004 forbids the warning today)

C-004 explicitly forbids deprecation warnings on `--feature` in this tranche unless approved during plan. None was approved, so all 22 callsites use `hidden=True` only — no warning is emitted. Operator scripts that pass `--feature <slug>` after the alias is hidden from `--help` get no signal that the alias is deprecated.

**Recommendation for a future tranche**:
- File a GitHub issue: "Sunset `--feature` alias — add deprecation warning under explicit env-var control".
- The hardening tranche should resolve a Decision Moment on the sunset window (e.g., warn for 1–2 minor versions, then remove).
- The `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` env var (already documented at `docs/reference/environment-variables.md`) is the natural escape hatch for noisy CI environments.

---

## FU-2 — `mark_invocation_succeeded()` covers ONLY `agent mission create --json` (RISK-2)

**Source**: mission-review.md RISK-2
**Severity**: LOW
**Status**: scope-narrowed-intentionally

Per WP06 plan T029, `mark_invocation_succeeded()` was deliberately scoped to the `agent mission create --json` success path only. Auditing every other JSON-emitting `agent` subcommand (`tasks status --json`, `mission branch-context --json`, `mission finalize-tasks --json`, etc.) was explicitly OUT OF SCOPE for FR-008. The motivating symptom (#735) is fixed for the named command; the same symptom may recur in any other JSON command path that triggers an atexit shutdown warning.

**Recommendation for a future tranche**:
- File a GitHub issue: "Extend `mark_invocation_succeeded()` to every JSON-emitting `agent` command".
- Each callsite must come with a failure-path test that asserts the warning STILL fires when the command exits non-zero.
- Inventory the JSON-emitting agent commands as the first WP step; the inventory itself is forward-looking work.
- Update `contracts/mission_create_clean_output.contract.md` to a more general contract that names the full inventory (or fork a sibling contract per command path).

---

## FU-3 — Two cooperating writers to `status.events.jsonl` with incompatible schemas (RISK-3)

**Source**: mission-review.md RISK-3
**Severity**: LOW (already mitigated by FR-010 fix at the reader)

WP08 fixed the symptom in `read_events()` with an `event_type`-presence guard. The deeper architectural concern — two cooperating subsystems (status emitter and Decision Moment Protocol) writing incompatible-shaped events into the same file — was not addressed (and rightly so; the spec explicitly scoped FR-010 to the reader). Any new reader added in future work that bypasses `read_events()` and parses lines directly will hit the same `KeyError('wp_id')` bug. The `# Why:` comment in `src/specify_cli/status/store.py:207-221` makes the trap visible to future authors, which is the lightest-touch mitigation.

**Recommendation for a future architectural tranche**:
- File a GitHub issue: "Formalize event-type-discriminated reader hierarchy in `src/specify_cli/status/`".
- Options to consider in plan:
  1. Split `status.events.jsonl` into `lane.events.jsonl` + `decision.events.jsonl` (single writer per file). Preserves backward compatibility with reader migration.
  2. Promote `wp_id` to `Optional[str]` on `StatusEvent` and add a typed event hierarchy (`LaneTransitionEvent`, `MissionLevelEvent`). Preserves single-file storage.
  3. Add a generic event-type registry that `read_events()` consults to dispatch to per-event-type parsers.
- Whichever option is selected, update the existing FR-010 contract (`contracts/status_event_reader_tolerates_decision_events.contract.md`) to reflect the new design.

---

## FU-4 — `_stamp_schema_version` silent-return on missing file or YAML parse error

**Source**: mission-review.md Silent-failure rows 1-2
**Severity**: LOW
**Status**: addressed in this tranche's follow-up commit (see commit message)

The two `return` statements in `src/specify_cli/upgrade/runner.py::_stamp_schema_version` swallow real errors (missing `metadata.yaml` and YAML parse failures) silently. They long predate this mission and were not introduced or modified by WP01 (which only swapped the call ORDER, leaving the existing error-handling shape untouched). The trigger conditions are unrealistic in normal operation (every spec-kitty project has metadata.yaml after init) but remain a latent silent-failure surface.

**Resolution**: this tranche's follow-up commit adds `logger.warning(...)` calls before each `return` so future operators see a diagnostic if the trigger ever fires. The fix is small, self-contained, and adds no new behavior (the function still returns silently — the only change is that the log line records the cause).

---

## Forward planning

The four follow-ups above should be filed as four separate GitHub issues at PR-merge time. FU-4's GitHub issue can immediately close as `verified-already-fixed` (cite this tranche's follow-up commit). FU-1, FU-2, FU-3 stay open as candidates for future hardening tranches.
