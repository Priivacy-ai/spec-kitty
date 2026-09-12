# Tracer: Approach

## 2026-08-14 — Arbiter ruling applied (fixer pass)

An adversarial squad HALTed spec review with three surviving severity-4 findings. An arbiter (`paula-patterns`, opus) ruled OTHER: the squad's three findings were upheld but mostly downgraded, and the arbiter found a severity-5 defect none of the squad caught — FR-001 as written asked to "promote" `find_undeclared_requirement_citations` to blocking, but that function only fires when a section's declared-id set is empty; verified directly against the issue's own repro, it returns `[]`. Promoting it would ship a gate that never blocks on the mixed-declaration case #3396 exists to catch.

Applied the ruling as a net subtraction, not a rewrite from scratch: reframed FR-001 (and the adjacent Context paragraph, C-001) around a NEW per-token predicate rather than a promotion; recorded the corpus measurement already taken (9/368 = 2.45%, document-scoped, zero true positives, all description-column citations) directly in Story 4/FR-005 instead of deferring it; deleted the invented <=2% ceiling, the true-positive/false-positive/ambiguous-block three-bin scheme, and the post-plan adversarial-squad exception-approval clause (FR-006, most of C-006's prior content) since a known, already-above-invented-ceiling measured rate makes that apparatus not just redundant but actively wrong; replaced the CI-gate design with a frozen, shrink-only corpus fixture under `tests/` (charter Standing Order 5's `frozen-baseline-shrink-only-ratchet`), which is non-vacuous and not self-referential — it does not let a future, unrelated mission's spec.md determine this gate's colour, and does not ship already-red at 2.45%.

Left C-008, FR-003's step_id-vocabulary audit, and FR-010/NFR-005's per-guard teeth-test requirement untouched — the arbiter ruled those good, and they are the mission's real remaining content.

Net result: spec.md is shorter (-2 lines / -2,580 chars in the diff) with strictly more information recorded (both measured rates, the scope-decision rationale, the zero-true-positive finding) than before.

## 2026-08-14 — Plan phase

`spec-kitty plan --mission bare-prose-requirements-uncounted-01KZYV3C --json` scaffolded
cleanly, non-interactively, no prompt. Filled `plan.md` directly against the spec's
11 mandatory sections. The plan-phase investigation's main work was tracing production
control flow rather than inventing architecture: confirmed by direct code read (not
assumption) that (1) `_check_requirement_mapping_ready`'s early return on
`not tasks_dir.is_dir()` and the `_tasks_dir_ready` short-circuit in all three existing
consumers of `requirement_mapping_failures` reproduce exactly the shape that made
`_zero_declared_requirement_block` inert, so FR-002's fix must read the new signal
*before* that check, not merely add it after; (2) the composed `"tasks"` action is the
production-live vocabulary for the built-in `software-dev` mission type at the
tasks-finalize boundary (traced through `software-dev-default.workflow.yaml`'s
`actions:` block, `_should_dispatch_via_composition`, and `_dn_composition_dispatch`'s
short-circuit before `_check_cli_guards` is ever reached) — resolving FR-003's audit
requirement with a traced finding, not a guess; (3) the two non-runtime call sites
(`mission_finalize.py::_validate_requirement_mapping`,
`tasks_mapping_core.py::plan_mapping`) duplicate the runtime core's
missing/unknown/unmapped logic independently and needed their own, separate wiring —
this was not obvious from the spec text alone and required grepping the actual
`finalize-tasks`/`map-requirements` CLI command implementations to find.

Chose C-008 option (b) — explicitly narrow scope, leave `_is_requirement_heading`
unmodified — specifically because broadening it to also match "constraint" would pull
~88% of the corpus into the blocking detector's scope with no corresponding
false-positive re-measurement, and the mission's own operating instructions forbid
relitigating the already-measured 9/368 figure. This is recorded as a plan-phase
judgment call, not a spec ambiguity — the spec explicitly sanctions "explicitly document
as an accepted scope narrowing" as a valid C-008 outcome.
