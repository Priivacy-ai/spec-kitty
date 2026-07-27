# Post-Plan Adversarial Squad — Findings & Resolutions

**Date**: 2026-07-23 · **Phase**: post-plan, pre-tasks · **Base**: merged `main` `eb06ca176`.
**Lenses**: reviewer-renata (anti-laziness/rigour, Opus) · paula-patterns (related-surfaces, Opus) · curator-carla (fidelity/roadmap, Sonnet).
**Verdict pre-amendment**: NOT ready for `/spec-kitty.tasks` (3 BLOCKER + 5 MAJOR + several MINOR). All code-level claims verified accurate; gaps were in rigour mechanics + one scope gap. **Post-amendment**: resolved.
**Operator decision (scope BLOCKER)**: **Add config-driven selection** — deliver SC-001 for real.

## BLOCKERs → resolutions

| # | Lens | Finding (verified) | Resolution |
|---|------|--------------------|------------|
| **B-sel** | carla | The "shared factory" `resolve_scope_source` only ever builds `GateCoverageScopeSource` (hardcoded pytest); `DeclaredCommandScopeSource` is constructed **nowhere in production** (`grep` = 0). FR-008's unconditional injection makes `_capture_baseline_via_config` (honors a consumer's `review.test_command`) **permanently unreachable**, and **SC-001** is only exercisable via a synthetic injected test, never a real repo. `scope_source.py:51-55` says the selection wiring "lands with #2873" — no FR adds it. | **NEW FR-014 + IC-14 (operator: add selection).** `resolve_scope_source` branches on `review.test_command` (present/non-pytest → `DeclaredCommandScopeSource`; else `GateCoverageScopeSource`), keeping the config path alive via the portable source. SC-001 restated as achievable against a real repo. Fix the stale `scope_source.py:51-55` comment + `docs/development/review-gates.md:174` (part of FR-014/FR-013). Update the FR-003/FR-008/NFR-005/FR-010 test matrix to include the selected `DeclaredCommandScopeSource` path. |
| **B-golden** | renata | The NFR-001/006 behavior-preservation goldens have **no carrier IC** and re-improvise a mechanism that **already exists canonically**: `tests/review/test_transition_gate_parity.py` + `tests/review/fixtures/parity/_capture.py` (captures against a pinned base, asserts `HEAD==base`, machine-emits `base_commit`, rejects hand-typed SHAs). Referenced **zero** times → an implementer could snapshot HEAD *after* the deletion (circular-oracle trap); also violates CLAUDE.md "use canonical sources". | **NEW IC-00 (WP-A entry, red-first)** + **NFR-007**: adopt the canonical `_capture.py` harness; capture NFR-001 (registry) **and** NFR-006 (override, non-empty scope) tuples against the pinned base, commit them with the machine-emitted `base_commit` provenance **before** IC-02's deletion; point NFR-001/006 replay at `test_transition_gate_parity.py`. Pin the base SHA = `eb06ca176`. |
| **B-vacuous** | renata | NFR-006's override-tier golden can pass **vacuously** — `run_scoped_tests_at_head`/`evaluate_with_scope` only execute on a **non-empty** scope, which no golden case is required to drive; "functional assertion" would degrade to an import assertion. | **NFR-006 amended**: enumerate, per kept symbol, the golden case that drives its live path — specifically an override case with a **non-empty derived scope** so `evaluate_with_scope → run_scoped_tests_at_head` actually run. "Functional" = the symbol's body executes in ≥1 golden case, not that it imports. |

## MAJORs → resolutions

| # | Lens | Finding | Resolution |
|---|------|---------|------------|
| M-B1 | renata | IC-09's B1 red-first is hand-waved, and B1's buggy path is **dormant on base** (a workflow-routed test isn't red on `main`). | **Split IC-09**: name the red-first carrier = a **direct** `capture_baseline`/`_capture_baseline_via_scope_source` unit test with `DeclaredCommandScopeSource` + a **worktree-relative** `--junitxml`, asserted red on the base *before* the relocate fix. Specify the relative `--junitxml` resolves against `cwd=tmp_worktree`, not process cwd. |
| M-inv | renata | FR-004 "no coverage lost" for the retired tests rests on an unchecked prose inventory. | **FR-004 amended**: the coverage-parity inventory is a **committed artifact reviewed at gate**; each retired test maps to a **named surviving test id** or an explicit "not carried forward because X". |
| M-mut | carla | `test_pre_review_scope_singlesource.py` is **not** a duplicate — it's the only mutation-bite proof that census derivation consults **live CI topology** (`_gate_coverage` vs real `.github/workflows`); the surviving `scope_source.py` copy has no equivalent (`test_scope_source.py` only asserts return-type). | **FR-004/IC-03 amended**: migrate the mutation-bite assertions **forward** onto `GateCoverageScopeSource`'s private `_resolve_excluded_catchall_groups`/`_glob_matches_file`/`_default_filter_groups`/`_default_composite_routing`, not merely "retire the file". |
| M-nfr5s | renata | NFR-005's "one helper, both sides" is asserted structurally in prose but only guarded behaviorally. | **NFR-005 amended**: add a structural assertion (capture + diff reference the **same** `scope_source_identity` symbol) so the guarantee matches the claim. |
| M-nfr5r | paula | NFR-005 equivalence uses a single root; the factory is called with **different roots** (baseline `main_repo_root` vs head `gate_repo_root`), and `source_identity` (class+parse-mode only) can't catch a `repo_root`-driven `test_command()` divergence. | **NFR-005 amended**: pin `test_command()` equality under **both** actual call-site roots; state explicitly that `source_identity` **excludes** the command by design (NFR-005 carries command equality). |

## MINORs → resolutions

- **IC-01 reword** (renata) — it's green-on-base characterization, not "red-first" → label "characterization precondition".
- **Pin ONE base SHA** (renata) — stated 3 ways (`eb06ca176` / `774143246` / `fa25daef7`); the golden capture asserts against `eb06ca176`.
- **Name the two `.value` sites** (paula) — `tasks_move_task.py:1120` (metadata, benign) + `:1574` (guarded `if effect.terminal:` → unreachable for non-terminal `SOURCE_MISMATCH`) as "verified non-branching" in IC-11.
- **Rename the mixin** (paula) — the file_to_scope-projection mixin is `ScopeBreakdownMixin` (renamed from `BreakdownScopeSource`, which was too close to the Protocol `ScopeBreakdownSource`).
- **Dead-symbol gate cross-module** (paula) — confirm `test_no_dead_symbols` keys on cross-module refs so post-deletion `_CompositeRoute` (cross-module-only) isn't false-flagged.
- **SC-002 "all members"** (renata) — state the console-ladder test discharges "every member enumerated"; the parity golden covers members the fixtures reach (D-3 rightly declines an exhaustive `list(GateOutcome)` golden).
- **C→IC traceability** (carla) — extend plan.md's "no orphans" line to enumerate `C-001..C-006 → IC/section`.
- **WP-A/WP-B same-file overlap** (carla) — IC-02 (~450 LoC delete) + IC-06/07 (edits at `:881,:1013`) touch `pre_review_gate.py`; flag the rebase-collision surface so tasks doesn't schedule them as truly-simultaneous same-hunk edits.

## Positive confirmations
- All 6 locked decisions (D-1..D-6) carried faithfully; fold-squad's 4 plan-time items threaded through spec→research→data-model→plan→contracts and re-confirmed against the repo (`SYMBOL_TO_MODULE==157`, the `:1184` fall-through, the `timezone` import, the `ruff.toml` entry).
- IC-11 fail-open is genuinely falsifiable (the allowlist assertion would fail if someone edited the filter); the 8-test migration is a real red-first mechanic.
- Two-signal `ClassVar` predicate + factory hoist are sound + cycle-free against the real code; FR-009 compare structurally cannot fire on the override tier; keep-live set complete; half-B not foreclosed; terminology clean.

## Net amendments applied to spec.md / plan.md / data-model.md
FR-014 (selection) + NFR-007 (canonical golden harness); IC-00 (golden capture) + IC-14 (selection); IC-09 split; FR-004 (gated inventory + mutation-bite migration); NFR-005 (structural + dual-root) + NFR-006 (non-vacuous); mixin rename; IC-01 reword; base SHA pinned; C→IC traceability; the `.value`/mixin-name/dead-symbol/WP-overlap notes. Stale `scope_source.py:51-55` + `review-gates.md:174` comments folded into FR-014's implement scope (code, not planning artifact).
