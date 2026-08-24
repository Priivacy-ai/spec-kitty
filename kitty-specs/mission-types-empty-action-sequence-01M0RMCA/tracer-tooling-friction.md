# Tracer: Tooling Friction

No friction encountered during spec authoring. `gh issue view 3701 --repo Priivacy-ai/spec-kitty --json title,body,comments` returned cleanly once `GITHUB_TOKEN` was unset (as instructed by the mission brief); the mission scaffold (`meta.json`, stub `spec.md`, `checklists/`, `research/`, `tasks/`, `status.events.jsonl`) was already present and correctly pointed at `fix/mission-types-empty-action-sequence-3701`; `.venv/bin/spec-kitty spec-commit --help` resolved without needing a fallback lookup.

## R4 round-2 fixer (2026-08-24)

`spec-kitty safe-commit` failed on its first invocation with "Missing argument 'FILES...'" when
called with only `-m` — it requires explicit positional `FILES...` arguments plus (soon,
becoming mandatory in v3.3) `--to-branch`. Not a defect, just worth flagging: the command's
`--help` text should make the required-soon `--to-branch` more prominent given it is currently
optional-with-deprecation-warning. Retried with the file path and `--to-branch
fix/mission-types-empty-action-sequence-3701` explicit and it succeeded.

## Plan phase (2026-08-24) — `spec-kitty plan --json` hangs indefinitely

`.venv/bin/spec-kitty plan --mission mission-types-empty-action-sequence-01M0RMCA --json` does
**not** complete. Two attempts: (1) foregrounded, hit the tool's 120s timeout with zero stdout;
(2) rerun with `< /dev/null` and a 60s `timeout` wrapper, exit code 124 (timeout-killed), stdout
showing only repeated warnings:

```
Warning: event journal capture failed: project sync store is locked (repeats suppressed; see the end-of-command capture summary)
Warning: Event routing failed: project sync store is locked
Warning: Event did not durably queue; dropping from publication
Warning: Explicit-context event capture failed: machine layout cutover did not publish within the bounded wait; the event is routed to the loud surface rather than dropped to legacy (repeats suppressed; see the end-of-command capture summary)
```

(3) rerun a third time backgrounded (`nohup ... &`) and watched via a process-liveness monitor for
3 more minutes — the underlying `python .venv/bin/spec-kitty plan ...` process (confirmed via `ps
aux`, PID separate from its parent shell) was still alive with no further stdout; killed manually
(`kill -9`) rather than left to strand the session. No stray lockholder process was found for this
repo checkout in `ps aux` before any of the three attempts (a different, unrelated repo checkout's
`spec-kitty agent mission create` process was running concurrently on the machine, for a different
mission entirely — not a plausible lock contender for this repo's own `.kittify/` state). No
obvious lock file was found under this checkout's `.kittify/` (`find .kittify -iname '*sync*'`
found only `.kittify/sync-state.json`, not a `.lock` file) — the "project sync store" this warning
names appears to live elsewhere (per-user state, not per-checkout), so root-causing further was
out of scope for a plan-phase pass.

This is a genuine non-terminating hang, not a slow-but-eventually-completing command — worth
escalating to the ledger as its own finding (distinct from the `safe-commit` friction above),
since a plan-phase (or any phase) agent hitting this with no pre-existing `plan.md` to fall back on
would have no artifact to author into and would need to report BLOCKED.

**Why this did not block this mission's plan phase**: `plan.md` already existed at the expected
path (`kitty-specs/mission-types-empty-action-sequence-01M0RMCA/plan.md`), left over from an
earlier scaffold pass (stale placeholder content, still shaped like an older template revision —
"Constitution Check" / "Parallel Work Analysis" sections that do not match the current canonical
`packs/built-in/missions/software-dev/templates/plan-template.md`, which uses "Charter Check" /
"Implementation Concern Map" instead — a second, smaller piece of drift worth flagging separately
from the hang itself). Since the scaffold command's job is to *locate* `plan.md`, and it was
already located, this plan was authored by directly editing that file in place rather than
re-attempting the hanging command a third time, and — per this mission's explicit
reflexive-failure clause — without ever hand-editing mission *state* (`meta.json`,
`status.events.jsonl`) to route around the hang. Reported back to the plan-phase orchestrator as
required.
