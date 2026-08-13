# Tracer: design decisions — org-pack-drg-root-graph-guard

Charter standing order 3. Decisions whose rationale would otherwise live only in commit
messages or the plan's prose — seeded at plan time with the five binding operator/orchestrator
decisions this mission inherits, plus the plan-specific decisions made while turning them into
a concrete design.

## Binding decision 1 — Fix shape: guard AND scan `drg/`, not either

**Decision**: Guard `_drg_helpers.py:87` with a `has_graph_files`-style check, **and** make the
org branch also look for graph content at `<org_root>/drg/`.
**Alternatives considered**: guard-only (stop raising, but never actually load `drg/` content).
**Rationale**: guard-alone closes the P0 (total zeroing) but leaves every *correctly-authored*
pack — the guide only documents the `drg/`-only layout — with its own DRG edges permanently
unloaded: a smaller, still-silent residual drop, and the only fix that makes a guide-compliant
pack fully functional is loading both.

## Binding decision 2 — Scope: #3384 only, #3385 stays separate

**Decision**: This mission's file set is `_drg_helpers.py` / `action_doctrine_bundle.py` +
tests only; no touch to `kind_vocabulary.py`.
**Alternatives considered**: fixing both #3384 and #3385 together since the issue text says
they "compound."
**Rationale**: different file, different call chain (`kind_vocabulary.py`'s activation-filter
path vs. `_drg_helpers.py`'s graph-load path), independently P0-class, independent regression
test. Bundling them would grow the diff past smallest-viable-diff for no shared mechanism.
**Consequence stated plainly** (per the operator's own answer): even after this mission's fix
lands, `charter activate` on any artifact still silently drops org-pack artifacts via #3385 —
the PR description must say so, so nobody closes #3385 believing this mission covered it.

## Binding decision 3 — Procedure-count assertion: `--json` for four kinds, plain-text for procedures

**Decision** (from the spec ruling, SPEC-FRESH4-001): assert directives/tactics/styleguides/
toolguides via `charter context --action <a> --json`'s typed arrays; assert the procedure count
via the plain-text render's Procedures section (`bootstrap_text.py:106`).
**Alternatives considered**: add a `procedures[]` array to the `--json` payload in this mission
(rejected — the payload is a versioned public contract; extending it is real scope growth on a
narrow P0 fix, filed instead as follow-up #3389); count procedures out of the top-level
`references` link set (not confirmed feasible — depends on unconfirmed kind-filterable URN
shape); drop the procedure assertion entirely (rejected — procedures are one of the five kinds
the bug zeroes; dropping it would weaken the mission's own non-vacuous gate).
**Rationale**: `build_disclosure_payload` (`progressive_disclosure.py:325`) delivers `procedure`
via `extra_delivered`, not a typed array — its own docstring says so. The plain-text render
already has a dedicated Procedures row. Splitting the assertion across both surfaces keeps all
five zeroed kinds covered without a contract change.

## Binding decision 4 — Topology: `lanes`, no coordination branch

**Decision** (create-time, irreversible, not this plan's to revisit): per-WP lane worktrees for
`sk-implement`, no coordination branch, since this is a single-PR mission.
**Rationale** (context, not re-litigated): the mission is small and cohesive enough that a
separate coordination branch would add process overhead with no real parallelism payoff — the
functional change is one function's evolution in one file.

## Binding decision 5 — PR shape: one PR, not one-PR-per-WP

**Decision**: ships as ONE PR. Explicitly evaluated in the plan (see plan.md's "PR Shape"
section) and judged right-sized — not recommended for a split.
**Rationale**: the entire functional change is IC-01→IC-02→IC-03, all sequential edits to the
same function (`load_validated_graph`'s org-layer branch, factored through `_load_org_layer`),
plus one documentation-only touch and one new test module. This is far below the scale that
would warrant flagging a split to the operator.

---

## Plan-specific decision — `OrgDRGFragmentError` is deliberately NOT a `DRGLoadError` subclass

**Decision**: the new exception raised for a malformed `drg/` fragment does not inherit from
`DRGLoadError`.
**Alternatives considered**: subclass `DRGLoadError` and add a new, narrower `except` clause in
`_load_action_doctrine_bundle` that re-raises only for the org branch; catch `DRGLoadError` in
`_load_org_layer` and set a sentinel/flag the caller checks.
**Rationale**: a `DRGLoadError` subclass would still match `_load_action_doctrine_bundle`'s
existing bare `except DRGLoadError as exc:` clause (Python `except` matches subclasses), so it
would still be silently swallowed unless that clause were also edited to special-case it —
growing the touched surface in a file C-001 wants minimally touched. A non-subclass type sails
past the existing catch by construction, achieving FR-004's org-branch-only narrowing with a
docstring-only change to `action_doctrine_bundle.py` instead of a functional one, and rides the
CLI's already-existing generic `except Exception` → `_emit_error` boundary for free.

## Plan-specific decision — `OrgDRGFragmentError` stays out of `_drg_helpers.py`'s `__all__`

**Decision**: despite not being underscore-prefixed by name, the new exception class is not
added to the module's `__all__`.
**Alternatives considered**: add it to `__all__` since it's a "real" exception type meant to be
asserted on in tests.
**Rationale**: `tests/architectural/test_no_dead_symbols.py` only counts callers under `src/`
(deliberately excluding `tests/`, per its own docstring), and this exception's whole design
point is that no other `src/` module ever needs to import and catch it by name — it propagates
uncaught, by design, all the way to the CLI's generic boundary. Adding it to `__all__` with no
real `src/` caller would make it an immediate dead-symbol-gate finding. Test files can still
import it directly by module path regardless of `__all__` membership (`__all__` only governs
`from module import *` and this specific gate's caller search) — verified against the gate's
actual mechanics, not assumed.

## Plan-specific decision — dedup scope is strictly the org-internal root+`drg/` sub-merge

**Decision**: `_dedup_org_layer_edges` only runs on the org-internal `merge_layers(root_graph,
drg_graph)` result, never on the outer `merge_layers(built_in, org)` / `merge_layers(_, project)`
calls.
**Alternatives considered**: run the same dedup pass on the final three-layer merge too, to
"future-proof" against a built-in/org duplicate.
**Rationale**: FR-003/FR-006(b) only pin the root-vs-`drg/` case; a built-in-vs-org or
org-vs-project duplicate is a different, untasked scope and should keep raising
`DRGValidationError` at the final `assert_valid` exactly as today — widening the dedup would be
an uncommitted, silent behavior change to an existing, working validation path, and a violation
of Locality of Change.

## Plan-specific decision — no Phase 0/1 planning docs generated (research.md, data-model.md, contracts/, quickstart.md)

**Decision**: this plan does not generate the usual Phase 0/1 artifact set.
**Alternatives considered**: generate placeholder versions for template-completeness.
**Rationale**: the operator's pre-specify clarification Q&A already resolved every
NEEDS CLARIFICATION a Phase 0 research pass would otherwise chase, and the three pre-existing
Key Entities in spec.md are composed, not newly modeled — there is no new data shape for
data-model.md to capture. Generating empty placeholders would be busywork; skip and say so
plainly rather than pad the artifact set.

## Entries

<!-- YYYY-MM-DD — Decision: [what]. Alternatives: [what else]. Rationale: [why this one]. -->
