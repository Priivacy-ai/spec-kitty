# Research: Read-Side Placement-Seam Migration

Synthesis of the pre-planning grounding squad (architect seam-map + researcher
reuse/#2921 lens). Anchors are absolute in the source.

## Settled context

- **Parent #1878** (deferred item 1: migrate direct-placement call sites onto the canonical resolver). #2922 is P2 tech-debt, deliberately unmilestoned (program-sized).
- **#2920 hardened the seam** `PlacementSeam.read_dir(kind)` (`mission_runtime/resolution.py:1404`) → `resolve_artifact_surface(:1634)`: kind-aware, TOTAL over (topology × CoordState), fail-loud (`CoordinationBranchDeleted`) when a coord partition is required but its branch is DELETED; sanctioned degrades for EMPTY/UNMATERIALIZED. But it did NOT migrate the pre-existing bypassers (explicitly out of #2920 scope).
- **Write-side precedent** (#2963/E, merged): consolidated hand-rolled resolve-or-degrade copies onto one kind-parameterized helper + a whole-tree AST write gate. Mirror this shape for reads.

## The two bypass families (migration cost differs)

- `resolve_planning_read_dir(root, slug, kind=K)` — **~44 caller files**, already kind-aware; swap to `read_dir(K)` is near-mechanical BUT **lenient→fail-loud** (a real per-site behavior change).
- `candidate_feature_dir_for_mission(root, slug)` — **~33 caller files**, **kind-blind**; each needs a declared `MissionArtifactKind` (the hard bucket).
- Deduped total: **~60 non-def `.py` modules** (list: scratchpad `bypass_files.txt`). Highest concentration: `cli/commands/agent/workflow.py` (17), `workspace/context.py` (7), `merge/executor.py` (6), `coordination/status_transition.py` (6).

## Reuse map (extend, do not duplicate)

| Target | Location | Role |
|--------|----------|------|
| Read seam | `mission_runtime/resolution.py` (`read_dir:1404`, `resolve_artifact_surface:1634`, `placement_seam:1754`) | The one kind-aware read authority — migration target |
| Read primitives | `specify_cli/missions/_read_path_resolver.py` (`candidate_feature_dir_for_mission:1148`, `resolve_planning_read_dir:1349`) | The primitive authority — **sanction** (mirror `resolution.py` self-exclusion) |
| Shared scanner | `tests/architectural/_placement_whole_tree_scan.py` (`scan_scope()`, `is_sanctioned`, prefix/module sanctions) | REUSE for the read gate — do NOT fork |
| Write gate to mirror | `tests/architectural/test_no_write_side_rederivation.py` (AST grammar `_scan_checkout_grammar:672`, def-site discrimination, staleness twin-guards, bite tests) | Template for the read gate |
| Ratchet keys | `tests/architectural/_ratchet_keys.py` (`resolve_descriptor`) | Content-descriptor allow-list (drift-proof, shrink-only) |
| Behavioral read guard (NOT the gate) | `tests/architectural/test_read_surface_placement_guard.py` | Hardens seam behavior; its docstring DEFERS this migration — extend the family, don't rewrite |
| Exception | `CoordinationBranchDeleted` | Reuse; no new type |

## Decisions & rejected alternatives

| Decision | Rationale |
|----------|-----------|
| Classify every site before migrating | Lenient→fail-loud is a behavior change; blind migration would crash audit paths. |
| Diagnostic/audit/corpus-walk readers stay lenient (allow-listed) | They must tolerate half-materialized/deleted coord branches (doctor, dashboard, cutover audit, status aggregation). |
| Sanction `_read_path_resolver.py` + infra self-consumers | They ARE the read authority / resolution infra — migrating them is self-referential breakage. |
| Gate mirrors the STRUCTURAL write gate (`test_no_write_side_rederivation.py`) | The existing `test_read_surface_placement_guard.py` is behavioral and explicitly defers this. |
| Gate seeded-red with shrink-only allow-list / lands last | Else it blocks its own migration. |
| Keep `resolve_planning_read_dir`, migrate its callers | Collapsing it into the seam is Directive-044 unification — separate, larger scope. |
| **Rejected**: file-scoped blanket exemptions | paula SF-2 — a blanket escape; use site-level content descriptors. |
| **Rejected**: fork a second tree walk for the read gate | T035 shared-authority rule — reuse `scan_scope()`. |

## #2921 (folded in) — precise

- Bug: `task_metadata_validation.py:127` `frontmatter, body, padding = parse_frontmatter(content)` — `parse_frontmatter` (`template/renderer.py:23-53`) returns raw frontmatter TEXT as the 3rd element, but `build_document(fm, body, padding)` (`task_utils/support.py:215`) expects `padding` = trailing whitespace. At `:178` the raw text is fed into the padding slot → closing `---` glued to a duplicated stale frontmatter block spliced into the body.
- Minimal fix: `:127` → `frontmatter, body, _ = parse_frontmatter(content)`; `:178` → `build_document(frontmatter_yaml, body, "\n")`. Do NOT swap to `split_frontmatter` (returns a string, not the mutable dict).
- Red-first: drive the pre-existing `repair_lane_mismatch(task_file, dry_run=False)` (CLI entry `validate_tasks.py:192`); assert clean single-frontmatter round-trip + `validate_task_metadata == []`. Independent of #2922 (zero placement coupling).

## Hard cases (for IC-04/IC-05)

- `cli/commands/agent/workflow.py` (17 sites) — mixed intents, highest blast radius; own WP.
- `surface_resolver.py`, `write_target_degrade.py` — infra self-consumers → sanction.
- `status/aggregate.py`, `dashboard/scanner.py`, `_coordination_doctor.py`, `_cutover_doctor.py` — corpus-walk/diagnostic → keep lenient (allow-list) or use non-raising `declared_read_surface`.
- Multi-kind readers → split or document a single-kind anchor.
- Retrospective reads → `resolve_retrospective_home`, not `resolve_artifact_surface`.
- `src/runtime/next/runtime_bridge_identity.py` — shared-package boundary; confirm route.
- Primary-tree enumeration (Mission-E cutover files) — third pattern, OUT OF SCOPE, declare explicitly.
