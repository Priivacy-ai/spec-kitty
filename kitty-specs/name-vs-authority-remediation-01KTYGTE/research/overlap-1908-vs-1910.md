# Overlap & Rebase Reconciliation — PR #1908 (01KTYGTE) vs merged PR #1910 (01KTZVQ2)

**Author:** architect-alphonso (READ-ONLY investigation)
**Governance Op:** 01KV07VEY31YEQTCR22JQ3GHEM
**Date:** 2026-06-13

## Context

- OUR PR #1908, branch `feat/name-vs-authority-remediation-01KTYGTE`, mission #132 "name-vs-authority".
- Must rebase onto `upstream/main`, which absorbed **#1910** ("Coordination topology stabilization", merge `a7f744bce`, branch `pr/coordination-topology-stabilization-01KTZVQ2`, also labelled mission #132) — an INDEPENDENT overlapping implementation.
- Fork-point: our branch forked from `649781d68` (the #1895 merge). #1910 merged just after `4bc2a5bff`.
- #1910 body: "Fixes #1883, #1884, #1885, #1886, #1887, #1888, #1164, #1878".

## Shared files (ours ∩ #1910) — overlap classification

| File | Region(s) ours / theirs | Overlap class | Rebase resolution |
|------|-------------------------|---------------|-------------------|
| `src/runtime/next/runtime_bridge.py` | both replace `mission=unknown` stub in `query_current_state` with a fail-closed raise | **EQUIVALENT (competing exception type)** | **take-theirs.** Theirs landed `MissionNotFoundError(handle)` with `.error_code="MISSION_NOT_FOUND"`; the landed shared tests assert exactly that. Our `QueryModeValidationError`-enrichment approach FAILS those tests. Drop ours; keep theirs verbatim. |
| `src/specify_cli/acceptance/__init__.py` | both exclude accept-owned `{acceptance-matrix.json, status.json}` from the dirty-tree snapshot (C-GATE-2 / #1883) | **EQUIVALENT (theirs is superset)** | **take-theirs.** Same constant set, same porcelain-path helper, same feature-dir scoping. Theirs ALSO rewires `_check_lane_gates`/`_check_workflow_run_evidence` to the coord-resolved `read_feature_dir` (T028) — strictly more. Drop our helpers (`_filter_accept_owned_dirty`, `_accept_owned_relpaths`, `_porcelain_path`); keep theirs. |
| `src/specify_cli/missions/_substantive.py` → `is_committed` | both add a coord-ref fallback so a coord-only-committed artifact passes (FR-001 / #1884) | **EQUIVALENT (competing signature)** | **take-theirs for `is_committed`.** Theirs: `is_committed(file, repo_root, placement: CommitTarget|None=None)`. Ours: `is_committed(file, repo_root, *, authority_ref: str|None=None)`. Same defect, same `resolve_placement_only` source, different param shape. Theirs landed + has a `mypy --strict` ratchet test (`test_is_committed_coord_aware.py`) asserting the `placement` arg shape. Take theirs. |
| `src/specify_cli/missions/_substantive.py` → `_has_substantive_technical_context` + `describe_technical_context_gap` (FR-013 / #1896) | **OURS ONLY** — theirs does not touch the bullet regex or add the gap-describer | **COMPLEMENTARY** | **keep-ours.** Re-apply the bullet-tolerant peer-field regex and the new `describe_technical_context_gap` helper + `__all__` entry ON TOP of theirs. This is unique #1896 value. |
| `src/specify_cli/cli/commands/agent/mission.py` → `setup_plan` `is_committed` call | both reroute the call through `_resolve_planning_placement` (which pre-exists at fork-point, from #1895) | **EQUIVALENT (mirror of is_committed)** | **take-theirs** for the `is_committed(..., placement=_spec_placement)` call site. |
| `src/specify_cli/cli/commands/agent/mission.py` → `describe_technical_context_gap` wiring into `plan_blocked_reason` (FR-013 / #1896) | **OURS ONLY** | **COMPLEMENTARY** | **keep-ours.** Re-apply the `_plan_gap` blocked-reason enrichment on top of theirs. (Theirs rewrote this function heavily — 414+/51-; re-apply our ~8-line enrichment manually against the new structure.) |
| `src/specify_cli/cli/commands/implement.py` | OURS: `_resolve_bookkeeping_transaction_identifiers` mid8 routing (FR-007) + a comment. THEIRS: `_feature_dir_file_paths` worktree-leak guard + new `_planning_artifact_source_dir` + `_ensure_planning_artifacts_committed_git` (FR-005/#1887) | **COMPLEMENTARY** (disjoint functions) | **manual-merge: keep-both.** Re-apply our `resolve_transaction_mid8` routing in `_resolve_bookkeeping_transaction_identifiers`; keep theirs untouched. Only manual touchpoint is the import block at top (theirs added imports). |
| `src/specify_cli/dashboard/scanner.py` | OURS: rewrites `gather_feature_paths` for registry-backed coord detection (WP03). THEIRS: `_process_wp_file` title fallback (line ~741) | **COMPLEMENTARY** (disjoint functions) | **manual-merge: keep-both.** No textual conflict expected; verify the two hunks don't share context lines. |
| `tests/contract/test_next_no_unknown_state.py` | both rewrite the missing-feature-dir test | **EQUIVALENT (theirs wins via runtime_bridge)** | **take-theirs.** Theirs asserts `MissionNotFoundError` + `.handle` + `.error_code`. Must match the landed `runtime_bridge` exception. Drop ours. |
| `tests/next/test_query_mode_unit.py` | both rewrite `test_missing_feature_dir_*` | **EQUIVALENT (theirs wins)** | **take-theirs.** Same reason. |
| `tests/architectural/test_no_dead_symbols.py` | OURS: adds `_CATEGORY_C_WP_IN_FLIGHT_TOPOLOGY_AUTHORITY` allowlist block (surface_resolver symbols) + union entry. THEIRS: removes one grandfathered entry (`_branch_strategy_gate::ALREADY_CONFIRMED`) | **COMPLEMENTARY** (disjoint regions) | **manual-merge: keep-both.** Re-apply our new allowlist block + the `_SYMBOL_ALLOWLIST` union line on top of theirs. Trivial. |

### Tests each side owns separately (NOT a textual collision, but verify post-rebase)
- THEIRS adds `tests/specify_cli/missions/test_is_committed_coord_aware.py` (asserts `placement` signature).
- OURS adds `tests/specify_cli/missions/test_substantive_gate_formats.py` (asserts bullet-regex + `describe_technical_context_gap`). **Must update** any of our tests that asserted the `authority_ref=` signature — rewrite them to the landed `placement=` signature, OR retarget them to only the `describe_technical_context_gap` surface (which is uniquely ours).

## Topology-abstraction-collision verdict

**VERDICT: COEXIST — no collision. Our `surface_resolver` seam is uniquely ours and survives clean.**

The prompt's worry was that #1910's "WP01 coord-aware read primitive" might be a competing topology READ primitive rivalling our `coordination/surface_resolver.py` authority seam (`WorktreeTopology` / `classify_worktree_topology` / `is_registered_coord_worktree` / `CoordinationBranchDeleted` / R3 registry-disposes-name). It is not.

Evidence:
- #1910's "coord-aware read primitive" (WP01) is literally the `is_committed(..., placement=...)` overload over the pre-existing `resolve_placement_only`. Its own spec says: *"`resolve_placement_only` already exists … Import it; do not re-implement placement logic."* It is an artifact-**committedness** helper, not a worktree-topology classifier.
- #1910 touches **none** of our seam files: `coordination/surface_resolver.py`, `lanes/branch_naming.py`, `lanes/worktree_allocator.py`, `lanes/_git.py`, `doctrine/drg/migration/extractor.py`, `charter/context_renderers/authority_paths.py`, `src/doctrine/graph.yaml`, `tests/architectural/test_topology_resolution_boundary.py` — all confirmed clean (untouched by `4bc2a5bff..a7f744bce`).
- There is NO `WorktreeTopology`-equivalent enum, NO registry-backed `classify_*`, NO `CoordinationBranchDeleted`-style structured-error type anywhere in #1910's diff. #1910's read-path fix anchors on the coordination *branch ref* (git `cat-file -e <coord_ref>:<rel>`); ours classifies coordination *worktree directories* via the git worktree registry. Adjacent concerns, no shared mechanism.

There is therefore **no competing abstraction to drop or merge**. Our seam is net-new architecture #1910 never introduced. Keep it whole.

## Net residual value of #1908 after #1910 (what uniquely remains)

After dropping the EQUIVALENT changes, #1908 still carries substantial unique value:

- **Topology authority seam** — `coordination/surface_resolver.py` (`WorktreeTopology`, `classify_worktree_topology`, `is_registered_coord_worktree`, `read_worktree_registry`, `CoordinationBranchDeleted` R3 "registry disposes the name"). Net-new. (WP03)
- **Branch-identity seam** — `lanes/branch_naming.py` (`mission_branch_name_required`, `BranchIdentityUnresolved`, `resolve_transaction_mid8`, dual-era rule) — #1860/#1898. (WP04)
- **Cross-lane base composition** — `lanes/worktree_allocator.py` honoring `depends_on_lanes` (#1684), with `--base` composition regression test.
- **Git-existence consolidation** — `lanes/_git.py` (#1904, behavior-preserving).
- **DRG extractor walk** — `doctrine/drg/migration/extractor.py` (#1863) + `graph.yaml`.
- **Authority-path flip** (2.x→3.x) — `charter/context_renderers/authority_paths.py` + charter tests (WP07, #1911-era).
- **Doctrine deltas** — #1865/66/67 (toolguide schema, github-tracker, planning-and-tracking styleguide, tracker-organisation procedure, clean-linear-commit-history tactic). (WP06)
- **Topology ratchet** — `tests/architectural/test_topology_resolution_boundary.py` (FR-009). (WP09)
- **`_substantive.py` bullet fix (#1896, FR-013)** — bullet-tolerant Technical Context regex + `describe_technical_context_gap` + its blocked-reason wiring. UNIQUE; #1910 left the old non-bullet regex in place.
- **mid8 fail-closed routing in `implement.py`** (FR-007) — replaces the slug-zero-padded mid8 fabrication.
- **Dashboard scanner registry-backed coord detection** — `gather_feature_paths` rewrite (WP03), distinct from #1910's title-fallback hunk.
- **SonarCloud hygiene + coverage top-ups** on mission-authored files.
- **Mission docs / governance ledger** — spec, plan, tasks, research/, op records, CHANGELOG.

Legitimately still **Closes**: **#1860, #1684, #1904, #1863, #1896, #1865, #1866, #1867, #1898, #1911(-era flip), #1907, #1906** (verify each against final state) plus FR-007 (no dedicated ticket cited). #1888 was also in #1910's Fixes list — verify whether ours still adds anything beyond it.

## Tickets to DROP from our "Closes" (already closed by #1910)

| Ticket | Our FR | Action |
|--------|--------|--------|
| **#1884** | FR-001 (is_committed coord-ref) | DROP from Closes. Reframe FR-001 as **"verify-already-fixed-by-#1910"** — assert the landed `placement`-based `is_committed` satisfies our acceptance criteria; our coverage stays as a parity guard, not a closing fix. |
| **#1883** | FR-002 (accept idempotency / dirty-tree) | DROP from Closes. Reframe FR-002 as **verify-already-fixed**; theirs is a superset (adds coord-resolved lane gates). |
| **#1885** | FR-003 (query-mode fail-closed) | DROP from Closes. Reframe FR-003 as **verify-already-fixed** by #1910's `MissionNotFoundError`. Our `QueryModeValidationError` enrichment is dropped on rebase; if the richer `next_step` payload is still wanted, re-propose as a small follow-up on top of `MissionNotFoundError`, not as a closing fix. |

Also cross-check #1886/#1887/#1888/#1164/#1878 (all in #1910's Fixes) against any of our FRs to avoid double-closing.

## Go / No-Go + risk rating

**GO — rebase is safe. Risk: LOW-to-MODERATE.**

- No architectural collision (verdict above). The three EQUIVALENT code overlaps resolve cleanly by **take-theirs** (theirs is on main and tested); our versions simply drop out.
- The COMPLEMENTARY overlaps (`implement.py`, `scanner.py`, `_substantive.py` technical-context, `mission.py` plan-gap wiring, `test_no_dead_symbols.py`) are disjoint regions — expect a handful of small manual conflict resolutions, all keep-both.
- Our unique survivors (the whole seam set) are confirmed untouched by #1910 — zero-conflict re-apply.

**Recommended rebase mechanics:**
1. Rebase `feat/name-vs-authority-remediation-01KTYGTE` onto `upstream/main` (post-#1910).
2. For `runtime_bridge.py`, `acceptance/__init__.py`, `_substantive.py::is_committed`, `mission.py::is_committed` call, `test_next_no_unknown_state.py`, `test_query_mode_unit.py` → **take theirs** (`git checkout --theirs` / accept incoming) and drop our competing versions.
3. **Re-apply by hand on top of theirs:** the #1896 technical-context regex + `describe_technical_context_gap` + its `mission.py` blocked-reason wiring; the `implement.py` mid8 routing; the `scanner.py` `gather_feature_paths` rewrite; the `test_no_dead_symbols.py` allowlist block.
4. **Rewrite our tests** that asserted `authority_ref=` to the landed `placement=` signature (or retire those assertions in favour of #1910's `test_is_committed_coord_aware.py`); keep `test_substantive_gate_formats.py` (unique).
5. Strip #1883/#1884/#1885 from the PR "Closes:" footer; reframe FR-001/002/003 in spec/issue-matrix as **verify-already-fixed-by-#1910** parity rows.
6. Run `pytest tests/contract/test_next_no_unknown_state.py tests/next/test_query_mode_unit.py tests/specify_cli/missions/ tests/specify_cli/acceptance/ tests/architectural/` + `ruff` + `mypy` before push.

**Escalation flags (operator decision, NOT auto-resolvable):**
1. **FR-001/002/003 reframing** — these were core P0s in our mission spec/issue-matrix. Converting them from "Closes" to "verified-already-fixed parity" changes the mission's headline deliverable. Operator should confirm the reframe (and whether the now-redundant `QueryModeValidationError.next_step` richness is worth a follow-up ticket) before the PR description is rewritten.
2. **Two competing tickets labelled mission #132** — both #1908 and #1910 claim mission #132. Operator should confirm display-number / mission-identity handling so the dashboards/selectors don't collide (Mission Identity Model: `mission_number` is display-only, assigned at merge; #1910 already merged, so #1908's number assignment must not duplicate).
