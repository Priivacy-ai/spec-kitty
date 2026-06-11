# Closeout Review — Spec→Code Fidelity & Correctness (reviewer-renata)

**Mission:** execution-context-unification-01KTPKST
**Branch:** fixups/code-engine-stabilization (flattened topology, all 12 WPs merged + rebased)
**Reviewer:** reviewer-renata · **Date:** 2026-06-10
**Scope:** integrated, merged code vs spec (FR-001..FR-015, NFR-001..005, SC-1..SC-7, C-CTX/FAC/PLACE/RT/OMAP contracts). Per-WP correctness is assumed verified; this pass targets the **composed whole** and cross-WP seams.

---

## Verdict: **PASS (releasable)** — with 2 minor non-blocking findings + 1 documentation-accuracy nit

The integrated mission genuinely delivers its core thesis: a single resolved `MissionExecutionContext` (doc-09 fragment composite) assembled by exactly one builder, with status routed through the existing OHS facade, a real git-op guard, and a collapsed daemon-reaper. The parity ratchet is **fully green (21 passed, 0 xfail)** and proves CWD-invariance + flattened-topology end-to-end. No parallel resolver survived (SC-4/NFR-001 upheld). The fragments/facade/read-path/placement compose correctly — I found no seam where two WPs' assumptions disagree at runtime. The open items are export-hygiene/lint and one acceptance-check wording drift, none of which affect correctness.

---

## FR-by-FR fidelity (integrated)

| FR | Delivered? | Evidence |
|----|-----------|----------|
| FR-001 | ✅ Yes | `MissionExecutionContext` is a doc-09 fragment composite, not a field bag — all 7 fragments present with `__post_init__` invariants. `src/mission_runtime/context.py:84-230` (IdentityFragment, BranchRefFragment, WorkspaceFragment, StatusSurfaceFragment, ArtifactPlacementFragment, PromptSourceFragment, CommitTarget). Flat substrate preserved (NFR-001). |
| FR-002 | ✅ Yes | `resolve_action_context` is the sole assembler; duplicate read-path resolver collapsed — `candidate_feature_dir_for_mission` now *defined* in `_read_path_resolver.py:339`, `feature_dir_resolver.py` is a 67-LOC re-export shim. `src/mission_runtime/resolution.py:494`. |
| FR-003 | ✅ Yes | `_identity_for_request` anchors on `_canonical_primary_feature_dir` via the facade resolver (`resolve_status_surface`). `src/specify_cli/coordination/status_transition.py:153-229`. Raw readers strangled onto the facade. |
| FR-004 | ✅ Yes | Artifact placement = the **same** `CommitTarget` carried on `BranchRefFragment.destination_ref` — a structural identity, not a runtime check. `resolution.py:454-471, 542`. record-analysis/implement-claim placement comes from this fragment. |
| FR-005 | ✅ Yes | `materialize_if_stale` gated by `git_operation_in_progress`. `src/specify_cli/status/views.py:196-291` (`if _is_stale() and not git_operation_in_progress(repo_root)`). Detects rebase/merge/cherry-pick/revert. |
| FR-006 | ✅ Yes | Retrospect record relocated to tracked `kitty-specs/<slug>/retrospective.yaml` (`canonical_record_path`); legacy gitignored path kept as read-fallback only. `src/specify_cli/retrospective/writer.py:36-72`. |
| FR-007 | ⚠️ Verified-already-fixed | merge `status_resolver.py` has no independent feature-dir/surface derivation; consumes the surface transitively via the strangled writers (WP02-07). Issue-matrix verdict accurate; no parallel re-derivation found in `src/specify_cli/merge/`. |
| FR-008 | ✅ Yes | `_identity_for_request` (#1737), `CoordinationWorkspace.resolve` lock-serialization (#1357), visibility parity (#1572) — `status_transition.py` + `coordination/workspace.py`. Parity ratchet asserts primary↔coord identical. |
| FR-009 | ✅ Yes | analysis-report staleness keying is context-aware (shared with FR-005 git-op guard); placement context-aware. |
| FR-010 | ✅ Yes | Occurrence-map `moves:` block added as **optional** field (`occurrence_map.py:110,152,180,194`); `_parse_moves` returns `[]` when absent → C-OMAP-1 backward-compat holds. Schema + template + skill updated. |
| FR-011 | ✅ Yes | Parity ratchet **extended** (not forked) — 21 tests, dual-CWD + flattened synthetic fixture, **fully green, 0 xfail**. `tests/architectural/test_execution_context_parity.py`. |
| FR-012 | ✅ Yes | `mid8` single-derived in `IdentityFragment.derive` (one call site repo-wide); `target_branch` resolved once via `get_feature_target_branch` (`resolution.py:526`); `_find_feature_directory` silent fallback replaced by structured `MissionSelectorAmbiguous`/`StatusReadPathNotFound`/`ActionContextError`; `prompt_source_dir` routed via PromptSourceFragment. |
| FR-013 | ⚠️ Partial-but-justified | Only **2 of 5** symbols deleted (`append_event_log_batch`, `read_wp_lane_actor`). The other 3 (`EventLogWriteTarget`, `StatusContractError`, `StatusReadSource`) are now **genuinely live internals** of `status_service.py` (drive `EventLogReadContract`/`EventLogWriteContract`, which ARE in `__all__` + facade-consumed); they were **de-exported from `__all__`** instead. The "5 dead" premise was stale post-#1614 rebase. Issue-matrix documents this accurately. **No correctness impact.** |
| FR-014 | ✅ Yes | (a) Dashboard `scanner.py:579` uses read-only `materialize_snapshot`; no writing `materialize()` call remains in `dashboard/`. (b) Daemon singleton keyed on `DaemonOwnerRecord`; one reaper wired at spawn. |
| FR-015 | ✅ Yes | **One** `_is_process_alive` definition (`sync/daemon.py:218`); `owner.py` imports it, `dashboard/lifecycle.py:125` delegates. **One** kill path (`owner._sweep_daemon_process`) — `cleanup_orphan_sync_daemons` (daemon.py:1230), `orphan_sweep._sweep_one` (orphan_sweep.py:319) both delegate to it. SC-7 upheld. |

**NFRs:** NFR-002 (ruff clean on all 9 changed core paths; mypy clean on `context.py`+`resolution.py`) ✅ · NFR-003 (parity deterministic, 21 green) ✅ · NFR-004 (CommitTarget/ExecutionContext names reused, not coined; doc-09 fragments) ✅ · NFR-001/005 (read-path + parser + reaper collapse; net subtraction) ✅.

**Contracts:** C-CTX-1 (single resolution — one `IdentityFragment.derive` call site repo-wide) ✅ · C-CTX-2 (CWD invariance — parity ratchet) ✅ · C-CTX-3 (mid8/target_branch single-derivation) ✅ · C-CTX-4 (no silent fallback — structured `MissionSelectorAmbiguous`/`StatusReadPathNotFound`) ✅ (see Finding 2 nuance) · C-FAC-1/2 ✅ · C-PLACE-1 (one placement ref = destination_ref) ✅ · C-RT-1 (git-op guard) ✅ · C-OMAP-1 (backward-compat) ✅.

---

## Findings

### Finding 1 — `legacy_record_path` should be privatized [LOW · export-hygiene · non-blocking]
`src/specify_cli/retrospective/writer.py` — `legacy_record_path` is referenced only intra-module (3 sites) + a test; no external caller. Should be `_legacy_record_path` or de-exported. This is the **one real** F-009 finding. No correctness impact. **Recommended action:** privatize in the fan-out remediation (already routed to operator/randy per F-009 disposition).

### Finding 2 — F-003 acceptance-check wording is not literally met (documentation nit) [LOW · non-blocking]
findings.md marks F-003 🟢 FIXED, with acceptance check "`context resolve --action tasks` returns the same `current_branch`/`branch_matches_target` as `setup-plan`." Empirically, `context resolve` **does not surface those keys at all** (its schema is `ExecutionContext.to_dict()`, which never carried branch-match fields — verified: keys absent, not null). `setup-plan` correctly returns `current_branch: fixups/code-engine-stabilization`, `branch_matches_target: True`. The F-003 **root concern** (branch-derivation inconsistency / `target_branch` single-source) IS fixed — `target_branch` resolves correctly and identically across surfaces, and the original "None" symptom is gone. The drift is only that the *stated acceptance check* compares fields one surface intentionally omits. **No correctness impact.** **Recommended action:** correct the F-003 acceptance-check wording to assert `target_branch` parity (the actual single-source contract), or add the branch-match fields to `context resolve` if cross-surface parity of that derived field is desired (follow-up, not blocking).

### Finding 3 — `ReapResult` / `canonical_executable_scope` dead-code flags are false-positives [INFO · no action]
Confirmed the post-merge review's adjudication: `ReapResult` is the live return type of `reap_orphan_daemons` (`owner.py:610,630`, in `__all__`); `canonical_executable_scope` is called internally (`owner.py:629`). The dead-code scanner flagged them under its documented "public-API-consumed-only-by-tests / consumed-structurally" false-positive class. No deletion warranted. (BLE001 in `_auth_doctor.py:236` is pre-existing/out-of-scope per F-009 — confirmed not a mission-touched file.)

---

## Integration-seam assessment (the cross-WP whole)

- **Fragment composition (WP03) ↔ consumers (WP02/04/05/06):** clean. `_assemble_core_fragments` derives identity/branch/status/workspace once from the **canonical primary root** (never the lane-supplied root), so every fragment is CWD-invariant by construction. ArtifactPlacement reuses `branch_ref.destination_ref` rather than re-deriving — the FR-004 invariant is a *type identity*, the strongest possible form. No seam disagreement.
- **Read-path collapse (WP04) ↔ facade (WP02):** `_resolve_status_surface_dir` falls back to `candidate_feature_dir_for_mission` on malformed/absent meta — this is a *bootstrap-window* fallback to the canonical primary dir (documented), NOT the C-CTX-4 silent-wrong-path the spec forbids. The forbidden case (ambiguous handle / coord-missing) correctly raises structured errors. Acceptable.
- **Flattened topology (C-001):** `destination_ref.kind == FLATTENED` when no coordination branch, collapsing read==write==placement. WP08's directed out-of-map edit (resolution.py:424-430) classifies the no-coord case correctly. Verified live: `context resolve --mission 01KTPKST` resolves the right feature_dir + target_branch.
- **Daemon/dashboard (WP11/WP12) ↔ git-op guard (WP07):** the dashboard read path shares the same `git_operation_in_progress` detection; the daemon reaper is independent (missionless) and collapsed to one kill path. 37 targeted integration tests pass (singleton, no-clobber, occurrence-map). No shared-state seam issue.

## Dogfood findings ledger (research/findings.md)
6 fixed (F-001/003/004/005/007/008), 2 worked-around tooling-ergonomics items (F-002 safe-commit dir-args, F-006 record-analysis substring verdict) — both correctly identified as non-mission-FR follow-ups. F-001 fix verified live (`--mission 01KTPKST` now resolves via `_canonicalize_handle`). F-008 (lifecycle-action parity) verified green.

## Recommendation
**Releasable.** No blocking issues. Route Finding 1 (privatize `legacy_record_path`) and Finding 2 (F-003 acceptance-wording / optional branch-match field) into the existing F-009 fan-out remediation. File the two worked-around tooling gaps (F-002, F-006) as follow-up tickets per the dogfood ledger's own recommendation.
