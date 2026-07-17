---
affected_files: []
cycle_number: 1
mission_slug: mission-step-creatability-01KXQA6R
reproduction_command:
reviewed_at: '2026-07-17T15:26:09Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP07
---

# WP07 Review — Cycle 1 (REJECT)

Reviewer: reviewer-renata (claude:opus). Lane: lane-g. Base: `kitty/mission-mission-step-creatability-01KXQA6R`.

## Verdict: CHANGES REQUESTED — one blocking arch-gate failure

The core design is correct and I want to be explicit that almost everything
passed. The single blocker is a **binding architectural gate that this WP's
diff turns red** and that the implementer's activity log did not run. Under the
charter's Architectural Gate Discipline standing order a red arch gate the WP
itself introduced blocks approval.

## BLOCKER — Symbol-level dead-code gate is RED

`tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`
fails on this diff:

```
Symbol-level dead-code gate FAILED. The following public symbols are declared
in __all__ but no other src/ file imports them:
  - specify_cli.runtime.resolver::TemplateURNError
  - specify_cli.runtime.resolver::resolve_template_by_urn
```

Both symbols are added by WP07 and neither exists on the base mission branch,
so the failure is unambiguously WP07-introduced (the failure list contains
*only* these two symbols — the base is green on this gate). `resolve_template_by_urn`
and `TemplateURNError` are exported in `resolver.py`'s `__all__` but have **zero
production importers** — the only references are the module itself and the two
new test files.

This is the classic "designed-ahead-of-consumer public API" situation: the URN
lane is a real compatibility-contract surface (C-004, `contracts/name-urn-resolution.md`)
whose consumer (`charter context --include template:<id>`) lands in a later WP,
not this one. That is legitimate — but the repo has a **canonical way to declare
it**, and WP07 did not use it, so the gate is red.

### Why option 1 (wire a caller) is the wrong fix here
FR-010 and the contract both scope-bind this WP to "add the lane + a
by-URN==by-name equivalence test **only**; do NOT re-wire the name-based
creation path." Adding a real production consumer is out of this WP's scope.

### Required fix (option 4 — the scope-preserving one)
Add allowlist entries for **both** symbols to `_SYMBOL_ALLOWLIST` (resolve via
`resolve_symbol_key`/`key_tier` in the gate's `_symbol_key.py`), in the
appropriate category frozenset, each commented with the qualified
`module::Name`, a rationale (compatibility-contract URN lane per C-004 /
FR-010; consumer arrives with the `charter context --include template:<id>`
surface in a follow-up WP/mission), **and a follow-up tracker ticket** (per the
gate's FR-303 instruction) that tracks wiring the consumer. Then re-run the
gate green.

If the team prefers, option 2 (drop both names from `__all__` and let the tests
import them as un-exported internals) is acceptable *only if* the URN lane is
not meant to be a public surface — but the contract frames it as a public
compatibility lane, so the allowlist route is the better fit. Choose one and
make the gate green; do not leave the export unregistered.

Run to confirm:
```
uv run pytest tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported -q
```

## Everything else — PASS (recorded so the next cycle need not re-litigate)

- **Two lanes, not collapsed (C-004)** — PASS. `resolve_template_by_urn` is
  added alongside `resolve_configured_template`; the WP07 commit (`307dcd1db`)
  only adds code after the name-lane function — its body is untouched and its
  signature is unchanged. Name lane still reads
  `resolved_mission_type.template_set` (resolver.py:414) and terminates in
  `resolve_template(...)` (resolver.py:449).
- **Equivalence + override-wins (US3.2 / US3.3)** — PASS, genuine.
  `tests/runtime/test_resolve_by_urn.py` resolves real shipped templates
  (`software-dev/spec-template.md`, `tasks-template.md`) and asserts by-URN path
  == by-name path; the override test writes a real
  `.kittify/overrides/templates/spec-template.md` and asserts the URN lane
  returns it at `OVERRIDE` tier. The only mocking is `get_kittify_home` → an
  empty dir (legitimate global-tier isolation), not the resolution logic. A
  legacy-tier test also proves the full 5-tier chain is honoured.
- **C-002 scalar fence** — PASS, real and bidirectional.
  `test_urn_resolver_scalar_fence.py` AST-scopes to the URN function subtree and
  asserts zero `.template_set` attribute accesses (would catch a real
  violation), plus an anti-vacuous guard asserting the name lane *still* owns
  the scalar. The URN code references no scalar surface; importing
  `ResolvedMissionType` is not used and not required here.
- **Fail-closed (C-001)** — PASS. Absent/blank/wrong-prefix/blank-segment/
  unresolvable URNs all raise typed `TemplateURNError`; the unqualified-URN test
  proves no `software-dev` inference (no #2660 regression).
- **Convergence** — PASS. `resolve_template_by_urn` →
  `template_catalog.resolve_template_by_id` → `resolve_template(name, project_dir, mission)`,
  the same Stage-2 resolver the name lane terminates in.
- **Scope** — PASS. WP07 commit touches only the 3 owned files (resolver.py +
  the 2 new test files). ruff/mypy clean; `spec-kitty doctrine
  regenerate-graph --check` FRESH.

## Anti-pattern checklist
1. Dead code — **FAIL** (the blocker above: two exported symbols, zero
   production importers; fix via allowlist + tracker ticket).
2. Synthetic-fixture test — PASS (tests exercise the real resolver).
3. Silent empty return — PASS (no silent returns; every failure path raises).
4. FR coverage — PASS (FR-010 equivalence + override-wins asserted).
5. Frozen surface — PASS (name-lane creation path untouched).
6. Locked decision — PASS (no scalar reference; no mission inference).
7. Shared-file ownership — N/A (lane-g owned solely by WP07).
8. Production fragility — PASS (raises are on fail-closed input-validation
   paths, documented in the docstring).

Fix the one gate and this is an approve.
