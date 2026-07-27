# Issue matrix — doctrine-controlled-transition-gates-01KY51Z7

Per the spec-kitty-mission-review skill Gate-4. One row per GitHub issue referenced in spec.md / plan.md.
Verdict vocabulary: `fixed` · `verified-already-fixed` · `deferred-with-followup` · `in-mission`
(`in-mission` passes per-WP `approved`; it MUST be resolved to a terminal verdict before the mission merges to `done`.)

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2535 | Epic: Doctrine-controlled transition gates | deferred-with-followup | Umbrella epic. This mission delivers **half A** (strangler steps 1–4). Half B (step 5) is #2599. Epic stays open until half B lands. |
| #2595 | Extract ScopeSource port for gate scope resolution | fixed | WP02+WP03 delivered `ScopeSource` port + both impls + engine consumption (commits on feat). Closes #2595. |
| #2596 | Register pre-review engine as the first named gate handler | fixed | WP04 `GATE_REGISTRY` with `evaluate_pre_review_gate` as first handler on `for_review`. Closes #2596. |
| #2598 | Invert move-task gate hook to resolve active bindings | fixed | WP09 `_mt_run_transition_gates` activation-resolved dispatch; parity-through-hook green. Closes #2598. |
| #2534 | Pre-review gate leaks internal `tests.architectural._gate_coverage` into consumer repos | fixed | WP09 removed the always-on internal import; erroneous-activation import-spy proves a consumer never reaches it. Closes #2534 (pre-review facet by construction). |
| #2330 | Pre-review / gate assumes pytest + `src/specify_cli/` layout | deferred-with-followup | **Pre-review facet** closed in-mission (WP02/WP03 layout-agnostic `ScopeSource` + WP09). The remaining facets — the `mission accept` `src/`+`tests/` path-convention gate and the mission-review Python-only gates — are explicitly out of scope per **C-006** and remain open as follow-up. #2330 stays open. |
| #2599 | Mission D — executable ASSET gate (half B / epic #2535 step 5) | deferred-with-followup | Explicitly OUT of scope (**C-002**). This mission *unblocks* #2599 (declarative bindings + `handler_kind` seam) but does not implement it. Separate future mission — stays open. |
| #2468 | Promote mission-type to a full activatable ArtifactKind | deferred-with-followup | Decision recorded in the WP01 ADR (`docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md`): gates **reuse** the existing `mission_step_contract` kind (content-vs-relationship principle, **C-001**) rather than a new `gate` kind — #2468's promotion is deliberately *not* pursued here and stays open as its own consideration. |
| #2741 | Pre-review gate diffs the working tree, not the WP commit range (P1) | deferred-with-followup | **Inherited, not fixed** — the behaviour-preserving strangler preserves this by design (parity-through-hook against base). Follow-up: #2741 stays open as its own red-first bugfix mission. |
| #2803 | `review.test_command` resolution seam | deferred-with-followup | Adjacent seam; only partially touched (the ScopeSource becomes the single command authority for the pre-review gate, FR-011). Follow-up: #2803 stays open for the broader resolution — out of scope here, must not be re-opened as a regression. |
| #2801 | Pre-review gate skip-flag seam | deferred-with-followup | Adjacent to the inverted hook; out of scope. Follow-up: #2801 stays open — do not re-open as a regression of this work. |
| #2573 | Pre-review gate disable-env seam | deferred-with-followup | Adjacent (`_mt_pre_review_gate_env_disable_reason` reuses `SYNC_DISABLE_ENV_VARS`); out of scope. Follow-up: #2573 stays open. |
| #2843 | DRG relation-description parity + activation-gate consolidation | verified-already-fixed | Merged before this mission — base commit `e4ef6e850` includes it. This mission builds on its corrected `filter_graph_by_activation` stem→URN primitive (mirror-not-ride, per research.md). |
