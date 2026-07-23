# Fold-Candidates / Boyscout Squad — Findings & Resolutions

**Date**: 2026-07-23 · **Phase**: post-spec, pre-plan (mission HELD until PRs #2874 + #2820 land) · **Purpose**: pull in related tickets + find in-flight tidying before planning.
**Lenses**: curator-carla (fold-candidate ticket-mining, Sonnet) · paula-patterns (boyscout in-flight tidying, Opus) · architect-alphonso (adjacency + rebase-collision, Opus).
**Verdict**: **#2873's 13-FR envelope is the right scope — no external ticket worth folding.** Real value = plan-time rebase hardening + one trivial in-flight fold. Amendments folded into spec.md (FR-002/004/009/011/013, NFR-004, C-004) + the "Rebase & Fold Notes" section.

## Lens 1 — carla (fold-candidate ticket-mining)

Searched open issues + all 19 open PRs across the surface's keyword neighborhood. **No strong FOLD candidate.**

| # | Classification | Note |
|---|----------------|------|
| #2874 | SEQUENCE-BEFORE (operator-decided) | Shallow overlap — only `_mt_resolve_gate_baseline` read-dir; `implement_capture_baseline` (FR-008 target) untouched. Small textual rebase. |
| #2820 | SEQUENCE-BEFORE (operator-decided) | Zero file overlap with `review/` or our `tasks_move_task.py` region. |
| #2741 | STALE — appears already fixed | Working-tree-diff defect resolved by mission `merge-base-diff-ssot-01KX44SD` (`55d060016`, `7c18ade8f`). **Candidate to close as fixed**, not fold. |
| #2330 | OUT (by design) | Needs the LIVE `scope_source.py` census copy made language-neutral (L); our FR-001 only deletes the DEAD `pre_review_gate.py` duplicate. Blows C-001 envelope. |
| #2599 | SEQUENCE-AFTER | Half B; depends on this mission's FR-008–011 (a second head source hits the same false-`NEW_FAILURES` we close). |
| #2801, #2803, #2825, #2853, #2570/#2493/#2573/#2762/#2555 | UNRELATED | Same-file-different-region or keyword-only; folding any adds unrelated scope. |

**Caution (#2825):** pre-existing `test_no_dead_symbols` + `test_golden_count_ban` reds on `main` are the SAME gate family FR-002/FR-004 touch — confirm their pre-existing status on the base before attributing a failure to our diff (baseline-red-gotcha).

## Lens 2 — paula (boyscout in-flight tidying) — size S

| # | Finding | Disposition |
|---|---------|-------------|
| 1 | `baseline.py:25` unused `timezone` import + over-broad `ruff.toml:86` entry (`F401` clears once import gone; `S602` already stale — no `shell=True`) → tighten to `["ARG001","S314"]` | **FOLD into WP-C** (already rewrites `baseline.py` + must be ruff-clean per NFR-002). Added to FR-013. |
| 2 | `verdict_aggregation.py:48-51` `__all__` comment mis-describes `AggregateVerdict` (calls the return type an "input row") | **Fold-if-touched** (FR-011 opens this module); comment-only, no test. |
| 3 | `baseline.py:267` dead `mission_slug` param (the `ARG001`) | **OUT** — removing ripples into ~8 test callsites, mixes an API change into the correctness WP. Separate ticket if ever wanted. |
| 4 | Duplicate `"in_progress->for_review"` constant across `gate_registry.py:52` + `gate_bindings.py:68` | NOTE-ONLY — not S1192 (single per module); hoisting couples two independent modules for ~0 payoff. |
| 5 | `OWNING_ACTION_FOR_EDGE` effective-constant dict | LEAVE — intentional forward-compat (C-006; half A gates only one edge). |

**Cleared (no make-work):** no function over the 15 complexity ceiling on the surface; no `Path.cwd()` reaches in `review/*`; no TODO/FIXME; no effect-free exception handlers (all log/translate/fail-open); `scope_source.py` `__all__` deferral comment still accurate.

## Lens 3 — alphonso (adjacency + rebase-collision) — hold-then-plan is SOUND

- **#2874 golden count is STALE.** #2874 adds `_binding_role_for_lane` to the compat tuple → base becomes **157**; our `_mt_pre_review_gate_verdict` deletion is **157→156**, not 156→155. → FR-002/C-004/NFR-004 restated base-relative.
- **FR-009 must fold onto #2874's kind-aware read seam.** #2874 rewrote `_mt_resolve_gate_baseline` (`tasks_move_task.py:1286`) to read via `_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)`; FR-009's diff-time identity read MUST consume that, not reconstruct `feature_dir` (else latent coord-topology bug). → folded into FR-009.
- **FR-011 `SOURCE_MISMATCH` exhaustiveness:** block/terminal paths are member-explicit allowlists (`_TERMINAL_OUTCOMES`, the `NEW_FAILURES` block) → fail-open **by construction** (assert with tests, don't edit). **The gap** is `_mt_pre_review_gate_console_warning`'s trailing `return "…no new failures"` fall-through — a new member silently renders as a clean pass. → FR-011 now requires an explicit branch + a defensive `else` rendering `outcome.value` (closes the latent class). No `list(GateOutcome)`/exhaustive golden exists → blast radius = enum add + console branch + tests.
- **#2820 disjoint** (dossier `BaselineSnapshot` ≠ `BaselineTestResult`; no shared files). Benign watch-item: FR-009's field changes `baseline-tests.json` content hash → shifts a mission's dossier parity hash (runtime data, not a collision).
- **Sequencing verdict:** A→C / B-parallel (C-003) survives #2874/#2820 unchanged; plan against the post-#2874/#2820 tree.

## Net actions
- **Spec amended** (this commit): base-relative golden count; FR-009 kind-aware seam; FR-011 console branch + defensive else; FR-013 `baseline.py` import + ruff-entry fold; Rebase & Fold Notes section.
- **No WP-D / no external ticket folded.** Boyscout item 1 rides WP-C; item 2 rides FR-011 if the file is opened.
- **Offered separately** (not auto-done): close #2741 as fixed-by-merge-base-diff-ssot; the #2825 baseline-red confirmation at plan time.
- **HOLD stands:** no `/spec-kitty.plan` until #2874 + #2820 merge.
