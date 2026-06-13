# Mission Specification — name-vs-authority-remediation-01KTYGTE

> **Branch retarget (2026-06-12):** PR #1895's branch (`feat/doctrine-glossary-consolidation-01KTNWFC`) entered review/merge; this mission now lands on `feat/name-vs-authority-remediation-01KTYGTE` (branched from that head). All branch-contract references to the old branch resolve to the new one.


**Mission type:** software-dev · **Planning base / merge target:** `feat/doctrine-glossary-consolidation-01KTNWFC` (the PR #1895 draft branch; PR grows, stays draft until this lands) · **Topology:** flattened (coordination branch removed per F-001 precedent)

## Intent

One defect class, declared by the 3.x architecture and repeatedly violated in practice: *a name or string shape is trusted as authority with no cross-check against the declared authority* (git worktree registry, `meta.json`, the `Lane` enum, structured `error_code`s, `resolve_*` surfaces). This mission (a) binds the two remaining authority seams and ratchets them closed, (b) closes the LIVE 3.2.0 release-blocker P0s rooted in that class, (c) verifies-with-proof the P0s our previous missions already fixed, and (d) folds the ready doctrine refinements + the proceduralized authority-path flip + the DRG extractor walk gap.

Slice of **#1868** (canonical seams epic) and **#1666**; sequenced INDEPENDENT OF and PRECEDING #1802/Op-ADR consumers (per architect adjudication). Research basis: `research/research-p0-rootcauses.md` (debby), `research-authority-seams.md` (alphonso — normative for seam APIs + the §Decision-Table), `research-fold-cluster.md` (robbie — deltas + chain verification), `research-overlap-sequencing.md` (robbie — overlap + landing shape), `convention-enforcement-scan-2026-06-12.md` (randy + alphonso adjudication).

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | **#1884 (P0, ROOT-α):** `setup-plan`'s committed-spec gate (`mission.py:1821` → `_substantive.is_committed`) verifies spec presence against the **placement authority's ref** (`git cat-file -e <resolve_placement_only(...).ref>:<rel>`), not primary HEAD only. The verifier reads where the writer writes — one authority. | planned |
| FR-002 | **#1883 (P0, ROOT-β):** the accept gate is **idempotent across all modes** (incl. `--no-commit`/diagnose): the `git_dirty` snapshot must not trip on accept-OWNED writes from the same or a prior accept run. Fix shape: snapshot-before-write ordering and/or accept-owned-path exclusion at `acceptance/__init__.py:934` vs `:753-754` + `accept.py:365` commit gating. Re-running accept on an unchanged tree converges. | planned |
| FR-003 | **#1885 residual (ROOT-γ):** `runtime_bridge.py:3068-3087` — a genuinely-unresolvable mission handle returns a **structured error** (code + next_step), never the silent `mission=unknown, reason=None` stub. | planned |
| FR-004 | **Verification rows:** #1889 and #1885's reported symptom are FIXED on this tree (by PR #1850's FR-003 cascade — reproduced in research). Add pinning regression tests for both repro fixtures if absent, record proof, close tickets with evidence. Do NOT re-fix. | planned |
| FR-005 | **Topology authority seam (scan cluster A + promoted G-writes):** `is_registered_coord_worktree(path, *, repo_root)` + `classify_worktree_topology()` + `WorktreeTopology` enum in `coordination/surface_resolver.py`, wrapping the `git worktree list --porcelain` cross-check (exemplar `doctor.py:~3063`), injectable cached registry. Migrate the 7 sites (5 cluster-A predicates incl. `status_service.py`, `aggregate.py`, `dashboard/scanner.py`, `workspace/root_resolver.py`, `status_transition.py` + 2 G-write-lock sites `emit.py:388`, `work_package_lifecycle.py:58`). Name proposes; the registry disposes. | planned |
| FR-006 | **Branch-identity authority seam (cluster B):** no new module — extend `lanes/branch_naming.py` with fail-closed `mission_branch_name_required(...)` + `BranchIdentityUnresolved` (structured), fed `mission_id` from meta. Migrate the 8 sites (incl. legacy-shape-only parsers `core/vcs/detection.py`, `sync.py:823`, `manifest.py:156`, `orchestrator_api/commands.py:771`, `lanes/compute.py` ×3, `lanes/recovery.py` ×2, `aggregate.py:669`). **Dual-era rule (binding):** legacy `\d{3}-` AND mid8-era names both RESOLVE; only the unresolvable case (modern mission, identity lost) rejects with the structured error. Closes the #1860 class. | planned |
| FR-007 | **Cluster-C residual:** the `(slug.replace('-','')+"00000000")[:8]` fabrication idiom is eradicated from its 2 surviving sites — `coordination/status_transition.py:265` (names the on-disk transaction dir) and `cli/commands/implement.py:395` — replaced by FR-006's authority (or fail-closed). | planned |
| FR-008 | **#1889 decision table (normative: research-authority-seams §decision-table):** every consumer of "coordination_branch declared?" gets ONE answer across the 5 rows; the net-new row R3 (declared + worktree absent + **branch deleted**) raises a distinct, loud structured error (composes with upstream #1848's status-transition carve-out; never silent-fallback to primary). One `git rev-parse --verify` cost accepted. | planned |
| FR-009 | **Ratchet:** `tests/architectural/test_topology_resolution_boundary.py` (structure mirrors `test_safe_commit_import_boundary.py`): (1) coord-predicate (`-coord`/`".worktrees" in parts`) allowlist = the blessed seam modules only; (2) AST scan: zero unbackstopped `f"kitty/mission-{slug}"` composes outside `branch_naming`; (3) zero `+"00000000"` idiom occurrences. Strictness proven by rogue-injection before landing. Lands LAST. | planned |
| FR-010 | **Doctrine refinements #1865/#1866/#1867** (+ the two #1865 addenda): apply the drafted deltas (research-fold-cluster §1) to the styleguide (triage-snapshot reconciliation pattern, secondary-label coexistence, provisional default `priority:P2`+`triage:needs-revision`), procedure (canonical-tree carve-out incl. label-only-mutation permission), toolguide (pagination rule generalized to all gh list surfaces). DIRECTIVE_018: additive, no version bump. Regenerate DRG if reference blocks change. | planned |
| FR-011 | **Authority-path flip:** execute the chain recorded in ADR `2026-06-11-1` deferral section (verified zero-drift in research-fold-cluster §2): `authority_paths.py` default → 2 source prompts → regenerate agent copies → 2 governance-contract tests → 3 `tests/charter/` assertions → `charter.md:317` → twelve-agent parity baselines regenerated WITH the template change → full architectural green. All links in ONE work package; ADR deferral section amended (append-only) to "executed". | planned |
| FR-013 | **#1896:** the substantive-plan gate's peer-field regex aligned with the Language/Version regex (bullets tolerated) + blocked_reason names the offending format when fields exist but don't parse. Pinning test: a bulleted-but-real Technical Context passes. | planned |
| FR-012 | **#1863 extractor walk:** extend the DRG extractor to walk styleguide `references` (path-string form via the `_resolve_path_ref()` 6-pattern helper, research-fold-cluster §3) AND add the `references` field to the toolguide schema (currently `additionalProperties: false` blocks it); regenerate graph (+~27 `suggests` edges, 0 nodes); orphan sweep limited to the 7 self-healing legacy artifacts (the remaining ~20 need curation — out of scope, noted on #1863). | planned |

## Non-Functional Requirements

- **NFR-001:** behavior-preserving outside the named defect rows; zero modifications to existing passing tests except where a test pins the *defective* behavior (justify per-case).
- **NFR-002:** new/touched code passes ruff + mypy with zero issues, zero new suppressions; terminology canon enforced.
- **NFR-003:** **fail-closed over fallback** (binding, per architect adjudication + container invariant #4): no new silent name-derived fallback may be introduced anywhere in this mission.
- **NFR-004:** every fixed ticket gets a pinning regression test; verification rows (FR-004) get reproduced-proof evidence in the review notes.
- **NFR-005:** C4/ADR alignment — both seams live inside modules the C4 already assigns (surface_resolver = Execution/Runtime; branch_naming = Mission Management); if any WP moves that boundary, STOP and escalate.

## Constraints

- **C-001:** runs on `feat/doctrine-glossary-consolidation-01KTNWFC` (flattened topology); PR #1895 stays draft until this mission lands into the branch.
- **C-002:** upstream coordination-merge-stabilization surfaces: the two shared files (`status_transition.py`, `cli/commands/merge.py`) are touched only at the non-adjacent ranges identified in research-overlap-sequencing §2; no edits to their function ranges.
- **C-003:** no parallel mechanisms — each seam is THE single authority; consumers migrate, they don't wrap.
- **C-004:** #1844 (release pipeline) is OUT of scope (standalone CI fix, R-D verdict) unless its root cause proves to be a cluster-B mis-compose.

## Success Criteria

- **SC-1:** all four P0 tickets reach terminal verdicts: #1884/#1883 fixed-with-regression-test; #1889/#1885 verified-already-fixed-with-proof (+#1885 residual hardened).
- **SC-2:** the ratchet is green AND strictness-proven (rogue injections fail it); zero convention-only coord predicates / branch composes / fabrication idioms outside blessed modules.
- **SC-3:** doctrine refinements land schema-valid; the flip lands with all 7 chain links green incl. parity baselines.
- **SC-4:** full architectural suite green; no regression in the coord-merge-stabilization surfaces.

## Domain Language

"Authority" = the declared source a resolver must consult (git worktree registry, meta.json, branch_naming grammar fed by mission_id). "Convention" = a name/string shape. The mission's invariant: **name proposes, authority disposes.**
