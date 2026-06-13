# DRG Orphan Residual — WP05 (FR-009 / C-003 / D-C2)

**Mission:** `mission-lifecycle-dispatch-drg-closeout-01KV0S99`
**Work package:** WP05 — DRG curation
**Generated against:** `src/doctrine/graph.yaml` after stale-ref repair + orphan wiring.

## Summary

| Metric | Before | After |
|--------|-------:|------:|
| Nodes | 235 | 234 |
| Edges | 585 | 596 |
| Orphans (no inbound or outbound edge) | 26 | 14 |
| Phantom nodes (`agent_profile:java-implementer`) | 1 | 0 |

- **Stale references repaired:** 5 styleguides (1 truly-phantom target repointed to a
  real profile; 4 same-class subdir-path drifts repainted to the on-disk locations).
- **Orphans wired (12):** 9 Fowler refactoring tactics now cited by the refactoring
  procedure; `mutation-testing-workflow` tactic now cites the two mutation toolguides
  (wiring the tactic + both toolguides into the graph).
- **Residual orphans (14):** all are valid, deliberately-authored doctrine artifacts
  with **no single natural referent**. Per D-C2 / C-003 they are documented here, NOT
  deleted. None is a defect.

## Curation policy (binding — D-C2)

An orphan that is a valid, deliberately-authored doctrine artifact is **unreferenced,
not defective**. It is never deleted to shrink a metric. It is either wired to a real
inbound edge (when a natural referent exists) or documented as an accepted residual.
Only genuinely-retired (superseded/dead) artifacts may be pruned, each individually
justified. No bulk deletion occurred in WP05.

## Stale-reference repairs (FR-008)

| Source styleguide | Old (absent) reference | New reference | Rationale |
|-------------------|------------------------|---------------|-----------|
| `java-conventions` | `agent_profiles/built-in/java-implementer.agent.yaml` | `agent_profiles/built-in/java-jenny.agent.yaml` | Truly-phantom target (no artifact with that stem on disk); `java-jenny` is the real Java specialist profile (`specializes_from implementer-ivan`). Removes the phantom `agent_profile:java-implementer` node. |
| `java-conventions` | `tactics/built-in/tdd-red-green-refactor.tactic.yaml` | `tactics/built-in/testing/tdd-red-green-refactor.tactic.yaml` | Same-class drift: path pointed at a nonexistent flat location; artifact lives under `testing/`. |
| `python-conventions` | `tactics/built-in/tdd-red-green-refactor.tactic.yaml` | `tactics/built-in/testing/tdd-red-green-refactor.tactic.yaml` | Same-class drift; repainted to on-disk path. |
| `testing-principles` | `tactics/built-in/{tdd-red-green-refactor,acceptance-test-first,test-minimisation,test-boundaries-by-responsibility,test-pyramid-progression}.tactic.yaml` | `…/testing/…` | Same-class drift for all five; artifacts live under `testing/`. |
| `aggregate-design-rules` | `tactics/built-in/{aggregate-boundary-design,domain-event-capture}.tactic.yaml` | `…/architecture/…` | Same-class drift; artifacts live under `architecture/`. |

> Note: the extractor resolves these path references by filename stem, so the drifted
> paths already resolved to the correct URN nodes (no phantom node was minted by the
> subdir cases). They were repainted anyway so the reference *paths* point at real
> on-disk files — honest references that survive any future existence-checking of the
> resolver. Only `java-implementer` minted a genuine phantom node.

## Orphans wired (FR-009)

| Orphan(s) | Wired via | Relation | Rationale |
|-----------|-----------|----------|-----------|
| 9 Fowler refactoring tactics: `change-function-declaration`, `combine-functions-into-transform`, `consolidate-conditional-expression`, `extract-class-by-responsibility-split`, `inline-temp`, `introduce-null-object`, `replace-magic-number-with-symbolic-constant`, `replace-temp-with-query`, `retry-pattern` | `procedures/built-in/refactoring.procedure.yaml` `references` | requires | The refactoring procedure's step 2 ("Select the relevant refactoring tactics") orchestrates selection across the Fowler catalog. Citing the catalog entries it can select is a real doctrinal relationship; the other refactoring tactics were already reachable via cross-references between related tactics. |
| `toolguide:python-mutation-tools`, `toolguide:typescript-mutation-tools` (and the `mutation-testing-workflow` tactic itself) | `tactics/built-in/testing/mutation-testing-workflow.tactic.yaml` `references` | suggests | The workflow drives the language-specific mutation toolchains; citing the toolguides it operationalizes is a real "uses tool" relationship. Wires both toolguides (inbound) and the tactic (outbound). |

## Residual orphans (14) — accepted, valid, no natural referent

Each is a valid, deliberately-authored artifact. None is retired or duplicated. They
remain unreferenced because no existing artifact has a genuine doctrinal reason to cite
them; manufacturing an edge purely to zero the metric would be metric-gaming (prohibited).

| URN | Artifact | Why residual (not wired, not deleted) |
|-----|----------|----------------------------------------|
| `agent_profile:human-in-charge` | Human in Charge | Sentinel profile signalling a human-assigned WP. Wired at runtime (assignment), not via static doctrine edges. |
| `directive:DIRECTIVE_035` | Bulk Edit Occurrence Classification | Operational directive applied by bulk-edit missions; no built-in artifact requires it statically (charter/mission-scoped activation, not a built-in inbound edge). |
| `paradigm:atomic-design` | Atomic Design | Front-end design paradigm; activated per-charter for UI work, no built-in artifact in the shipped tree references it. |
| `procedure:documentation-gap-prioritization` | Documentation Gap Prioritization | Documentation-mission procedure; invoked by the documentation mission flow, not cited by another built-in artifact. |
| `styleguide:deployable-skill-authoring` | Deployable Skill Authoring Styleguide | Meta-styleguide for authoring spk skills; consumed by skill-authoring work, no doctrinal inbound edge. |
| `styleguide:reasons-canvas-writing` | REASONS Canvas Writing Styleguide | SPDD/REASONS styleguide; activated only when a charter opts into the SPDD pack. |
| `tactic:clean-linear-commit-history` | Clean Linear Commit History via Snapshot Chain | Post-merge history-compression tactic; applied at closeout, not referenced by another artifact. |
| `tactic:decision-marker-capture` | Decision Marker Capture | Communication tactic for capturing decisions; cross-cutting, no single owner artifact. |
| `tactic:documentation-curation-audit` | Documentation Curation Audit | Documentation audit tactic; cross-cutting, used by documentation work. |
| `tactic:no-parallel-duplicate-test-runs` | No Parallel Duplicate Test Runs | Testing-hygiene guardrail tactic; advisory, no natural owning procedure/directive. |
| `tactic:occurrence-classification-workflow` | Occurrence Classification Workflow | Bulk-edit classification tactic; pairs with DIRECTIVE_035 conceptually but neither is the canonical referent of the other (would be a circular metric edge). |
| `tactic:zombies-tdd` | ZOMBIES TDD | TDD increment tactic (explicitly named in D-C2 as a protected valid orphan); advisory, no single owning artifact. |
| `toolguide:python-review-checks` | Python Review Checks | Review-tooling toolguide; consumed by reviewer agents at runtime, not via a built-in static edge. |
| `toolguide:rtk-search-tooling` | RTK Interception and Search Tooling | System-tools toolguide; operator/runtime tooling, no doctrinal inbound edge. |

## Follow-up ticket (required — residual is non-empty, C-003)

The residual set is non-empty, so per C-003 a curation follow-up ticket is required
before #1863 closes. Tracking: future curation pass to evaluate whether any of these 14
gain a natural referent as missions/charters evolve (e.g. when an SPDD/documentation/
bulk-edit organizing procedure is added that would naturally cite them). **No deletion**
is in scope for that follow-up unless an artifact is shown to be genuinely retired.

> Orchestrator: file the curation follow-up ticket and record it in the #1863 issue-matrix
> row at the merge/accept gate. The residual ceiling is pinned at **14** by
> `test_shipped_graph_orphan_count_within_documented_residual`.
