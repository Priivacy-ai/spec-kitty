---
affected_files: []
cycle_number: 2
mission_slug: lifecycle-gate-execution-context-01KY72GQ
reproduction_command:
reviewed_at: '2026-07-24T10:51:34Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP17
---

# WP17 Review — REJECT (cycle 1)

Reviewer: reviewer-renata (independent scrutiny; orchestrator completed the mechanical commit 9ff898fe3).
Verdict driver: **Check #2 — accept-gate behaviour NOT preserved. An unacknowledged, empirically-demonstrated false-pass widening (C6 / C-010 violation) in the exact gate this mission hardens.**

Most of WP17 is correct and well-executed. The single blocking defect is narrow and fixable. Details below.

---

## BLOCKER 1 — `_is_accept_pipeline_own_write` widens the accept-owned exclusion to `status.events.jsonl` (false pass, C6)

`src/specify_cli/acceptance/__init__.py:146-152` — the new predicate routes on the *kind*:

```python
kind = kind_for_mission_file(path, mission_slug=mission_slug)
return kind in (MissionArtifactKind.ACCEPTANCE_MATRIX, MissionArtifactKind.STATUS_STATE)
```

`MissionArtifactKind.STATUS_STATE` maps from **two** basenames, not one — `src/mission_runtime/artifacts.py:187-188`:

```python
"status.events.jsonl": MissionArtifactKind.STATUS_STATE,
"status.json":         MissionArtifactKind.STATUS_STATE,
```

The retired `ACCEPT_OWNED_PATHS` was `frozenset({"acceptance-matrix.json", "status.json"})` — it did **not** contain `status.events.jsonl`. So the kind-based routing silently sweeps in a third path the filename set never excluded.

**Empirical proof of the behaviour change** (flat mission, `_accept_dirty_gate` on this branch):

| dirty path | original (flat) | WP17 (flat) |
|---|---|---|
| `status.json` | excluded (accept-owned) | excluded ✓ |
| `acceptance-matrix.json` | excluded (accept-owned) | excluded ✓ |
| `status.events.jsonl` | **BLOCKS** (not accept-owned; residue filter #3 does not run under flat) | **BENIGN** ✗ |
| `spec.md` | blocks | blocks ✓ |

Under a coordination topology the net result is unchanged (residue filter #3 already excluded it), so this defect is **flat-topology-specific** and was invisible to the coord-path tests.

**Why this is a false pass, not a latent-gap fix:** the accept pipeline only *reads* `status.events.jsonl` (`acceptance/__init__.py:660, 664, 867`) — it never appends to it (no `emit_status_transition` / `append_event` in the accept path; the writer is `status/store.py`, driven by `move-task`/`mark-status`). It is therefore **not** an accept-pipeline own-write, so it is not required for `accept ∘ accept` convergence. A dirty `status.events.jsonl` at accept under a flat mission is a genuinely-uncommitted append to the lane-state source-of-truth; the original gate correctly blocked it, and merging past it risks losing status state on the target branch — precisely the integrity property this mission exists to protect.

**Two independent confirmations that the widening is unintended, not a design choice:**
1. Your own convergence-test oracle now hardcodes `accept_owned_basenames = ("acceptance-matrix.json", "status.json")` (`tests/specify_cli/test_accept_gate_convergence.py`, WP17 diff) — the test says the accept-owned set is exactly those two, contradicting the production predicate that exempts a third.
2. The canonical owner itself agrees `status.events.jsonl` is *not* toolchain churn under flat: `is_coord_residue_churn` returns `False` for it under a flat/stored-topology mission. Your predicate is therefore **more lenient than the owner** — the opposite of "retire onto the owner."

**Root cause:** `STATUS_STATE` conflates the daemon-materialized view (`status.json`, an accept/daemon own-write, correctly exempt unconditionally) with the append-only log (`status.events.jsonl`, not an accept own-write). Kind-granularity cannot express "status.json yes, status.events.jsonl no." The docstring guards meticulously against the `ISSUE_MATRIX` widening of the residue leg but is blind to this two-basename conflation *inside* `STATUS_STATE`.

**Required fix (implementer's discretion on form):** scope the accept-owned predicate to the specific own-write paths — `acceptance-matrix.json` and the materialized `status.json` only — so `status.events.jsonl` is not swept in. Then add a red-first test pinning the invariant: **a flat mission with a dirty `status.events.jsonl` must still BLOCK accept** (this is the missing behaviour-preservation test; its absence is why the widening passed 125 green tests).

---

## Checks that PASS (no action needed)

- **Check #1 (per-symbol absence, C5):** `ACCEPT_OWNED_PATHS`, `ignores_primary_coord_residue`, and the four bundle symbols (`_BENIGN_EXACT_NAMES` / `_BENIGN_PATH_PREFIXES` / `_WP_TASK_PATTERN` / `_ROOT_TASKS_MD_PATTERN`) are all absent from `src/`. The 3 registry rows deleted; `_exclude_coord_owned.md` untouched (WP14's). Ratchet green (`test_exemption_registry_ratchet.py`, 12 passed).
- **Check #3 (survivor honesty) — PASS, genuinely.** The review-gate split is honest per-pattern: the status/self-bookkeeping arm (`status.events.jsonl`, `status.json`, `meta.json`) routes onto the owner (unchanged — these were benign in the review gate before via `_BENIGN_EXACT_NAMES` and remain benign). The four retained survivors (`lanes.json`, `.kittify/`, `tasks/WP##-*.md`, root `tasks.md`) each return `False` from `is_toolchain_generated_churn` (verified) — routing them on would regress the merge/accept gates (C6), so keeping them as a review-handoff-only survivor is correct. Registry row `_is_review_handoff_survivor_path.md` has real justification prose, `literals: (none)`, and a live symbol — symbol-presence arm holds. **Not** a WP15-style dodge. (Note: the accept-side defect is the *inverse* of a survivor dodge — an over-eager route-onto-owner, not a lazy survivor.)
- **Check #4 (dead field):** `ignores_primary_coord_residue` had zero external consumers on the base (confirmed via `git grep`), cleanly deleted; the two migrated tests now assert `kind_is_coordination_residue(...)` against the real authority.
- **Check #5 (quality):** ruff clean on all three files; the 2 mypy errors (`:254` subclass `TaskCliError`, `:680` return-Any) pre-exist on the base (245/671 in isolation) and sit on lines WP17 did not touch; no new suppressions; complexity fine.
- **Check #6 (handoff integrity):** single coherent commit; test migrations included; no half-applied retirement.

---

## Summary

Fix BLOCKER 1 (narrow the accept-owned predicate off the coarse `STATUS_STATE` kind + add the flat-mission `status.events.jsonl`-blocks red-first test). Everything else is approve-ready.
