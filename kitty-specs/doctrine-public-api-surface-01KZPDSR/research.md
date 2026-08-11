# Phase 0 Research — Doctrine Public API Surface

The design space for this mission was settled by the pre-spec research
(`docs/plans/doctrine/next-slice-wheel-mission-types-public-api-research.md`), the scoping
brief (`docs/plans/doctrine/3179-public-api-surface-scoping.md`), and the post-spec
adversarial squad (2026-08-10). This file consolidates the decisions; there are no open
`[NEEDS CLARIFICATION]` items.

## D-01 — Public surface = single `doctrine/api.py`, not a widened `doctrine.__all__`

- **Decision**: Introduce one `doctrine/api.py` module with an explicit `__all__` as the curated surface; keep `doctrine/__init__.py` minimal.
- **Rationale**: The enforced layering is `runtime → charter → doctrine`. Widening `doctrine.__all__` would legitimize runtime importing doctrine directly, contradicting the boundary. A dedicated `api.py` gives charter and the future wheel one import target without opening a runtime door. "Exactly one place" (US1) also requires a single module, not scattered per-subpackage `__all__`.
- **Alternatives considered**: (a) widen `doctrine.__all__` — rejected (legitimizes direct runtime import); (b) per-subpackage `__all__` only — rejected (not one enumerable place); (c) no api.py, rely on facades alone — rejected (the wheel needs an export manifest).

## D-02 — Consumption stays facade-mediated; api.py is for charter + wheel

- **Decision**: Runtime never imports `doctrine.api`; it imports `charter.*` facades that re-export from doctrine. `api.py` exists for charter and the packaged wheel's external contract.
- **Rationale**: Preserves C-001. The facade identity test already guarantees `charter.X is doctrine.X`, so there is no drift between the facade and the surface.
- **Alternatives**: let runtime import `doctrine.api` directly — rejected (same boundary violation, just relabeled).

## D-03 — Facades re-export symbols, not whole submodules

- **Decision**: Every facade re-export is a specific symbol (`load`, `evaluate`, `RoutingRecommendation`, `MissionTemplateRepository`, …), and consumers that currently use a doctrine submodule *as a module* (e.g. `invocation/executor.py` calling `loader.load()`) are migrated to symbol imports.
- **Rationale**: A whole-module re-export passes the `is`-identity check yet fronts the entire submodule, defeating curation (architect finding). Symbol-level keeps the surface enumerable.
- **Alternatives**: module-level re-export — rejected (curation-defeating).

## D-04 — INTERNAL-vs-migrate reconciliation (the post-spec HIGH)

- **Decision**: Any path a non-exempt runtime module imports **cannot** be pure INTERNAL. Each such path resolves to exactly one of: FACADE-ONLY (narrow charter door), enumerated management-surface entry (the consuming module joins the inbound-only allowlist with a rationale), or a ticketed permanent baseline exception. Only paths with **no** non-exempt consumer stay INTERNAL (and get a negative test).
- **Rationale**: Three independent squad lenses proved `pack_paths`, `drg.override_policy`, `missions.mission_step_repository`, `missions.step_projection`, `glossary_packs`, `spdd_reasons` are reached by non-exempt runtime today — a "no door, no exemption" INTERNAL label makes SC-001 unsatisfiable and creates permanent baseline residents the stale-entry check rejects.
- **Alternatives**: keep them INTERNAL and permanently allowlist — rejected (violates stale-entry invariant + SC-001).

## D-05 — Exemption is inbound-only; close the laundering conduit

- **Decision**: `src/specify_cli/doctrine/` may import doctrine (inbound) but must not re-export doctrine objects to non-exempt runtime (outbound). The `specify_cli.doctrine.config` re-export of `resolve_org_roots` et al., consumed by ~10 non-exempt sites, is closed by routing those consumers through the charter `resolve_org_roots` door.
- **Rationale**: Both string-ratchets match `doctrine.*`, not `specify_cli.doctrine.*`, so the conduit lets SC-001 read green while the semantic boundary leaks (architect HIGH).
- **Alternatives**: leave the conduit — rejected (boundary leak); ban the exempt subpackage entirely — rejected (it is the legitimate management surface).

## D-06 — Ratchet = sibling test, full AST, only-shrink baseline, laundering rule

- **Decision**: Add a sibling test in `test_runtime_charter_doctrine_boundary.py` that walks full ASTs (not just `tree.body`), matches absolute `doctrine`/`doctrine.*` with `ImportFrom.level == 0`, excludes `TYPE_CHECKING` and the enumerated management surface, uses an only-shrink frozenset baseline seeded from the census, and adds a first-party-re-export laundering rule. Lands early with the full baseline (red-first); migration shrinks it.
- **Rationale**: Keeps the module-level ratchet's empty-baseline "headline count" intact; the two failure modes want different messages; the stale-entry check proves each migration. Closes the runtime→doctrine half of #2986.
- **Alternatives**: extend the existing test to `ast.walk` in place — rejected (forces the module-level baseline to absorb 29 lazy files, destroying its "empty = migrated" signal); import-linter contract — rejected (repo enforces via pytestarch/AST, not import-linter).

## D-07 — Regression-delta gate, not "full suite green"

- **Decision**: The reliability gate is "no test green on the merge-base goes red on this branch," with pre-existing reds classified per the charter Pre-existing Failure Reporting Rule / DIR-013.
- **Rationale**: The repo has a known-red baseline (P0 reds, CI-env, stale-install). "Full suite green" is either unachievable or a rug that excuses regressions (reviewer MAJOR).
- **Alternatives**: "full suite green" — rejected (fakeable/impossible).

## D-08 — FR-010 isolated + behavior-locked by a golden DRG snapshot

- **Decision**: The complexity refactor is the last, independently-revertable work package. Capture a golden `regenerate-graph` snapshot on the base commit **before** refactoring; assert byte-identity after; every extracted helper carries its own focused test. Governed by the disciplined-refactoring / semantic-compression doctrine.
- **Rationale**: It is the highest-risk, most-fakeable slice and shares no file-touch with the boundary work; cognitive-complexity ≤15 is gameable by no-op helper extraction unless helpers are tested and the metric is measured on real load. Byte-identity on canonical regenerate output is a stronger guarantee than graph-equivalence and catches provenance/ordering drift (doctrine-daphne concession).
- **Alternatives**: fold it inline with boundary WPs — rejected (contaminates a low-risk deliverable with refactor risk); graph-equivalence check — rejected (weaker than byte-identity here).

## D-09 — Sonar debt fixed, not triaged

- **Decision**: Clear the 45 CRITICAL doctrine smells by code fixes only; NFR-005 forbids both code-comment suppressions and Sonar-UI Won't-Fix/False-Positive transitions during the mission window.
- **Rationale**: "Open CRITICAL → 0" is otherwise fakeable via UI triage without touching code (reviewer MAJOR).
- **Alternatives**: allow UI triage for genuine false positives — deferred; if a genuine FP is found, record it in the PR body with rationale rather than silently transitioning.

## D-10 — C-007 disambiguation + extension

- **Decision**: Treat "charter C-007 (`__all__` convention)" and "ADR 2026-04-25-1 C-007 (no-partial-cutover)" as two distinct rules, always qualified. This mission makes the per-mission scope decision to extend the charter `__all__` convention to `src/doctrine/` and records it.
- **Rationale**: Charter C-007 today binds only `charter`/`kernel`; citing it as pre-existing authority over doctrine is incorrect, and the dual-"C-007" overload is exactly the footgun the Terminology Canon warns about (doctrine-daphne).
- **Alternatives**: silently assume C-007 covers doctrine — rejected (mis-citation of record).
