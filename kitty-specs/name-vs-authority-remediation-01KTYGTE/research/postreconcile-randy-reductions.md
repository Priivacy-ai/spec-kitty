# Post-#1910-Reconcile — Reduction-Preservation / Wiring / Duplication Audit

**Profile:** randy-reducer (READ-ONLY, non-code-mutating)
**Governance Op:** 01KV0927XG6B59261E04SJTBYN
**Branch:** `feat/name-vs-authority-remediation-01KTYGTE` @ tip (`3afe347ea`, rebased onto upstream/main containing #1910)
**Date:** 2026-06-13
**Lens:** reduction-loss after take-theirs collision · phantom/dead code · duplication reintroduced by the reconcile

---

## 1. Reduction-survival table

All landed behavior-preserving reductions SURVIVED the rebase. Taking #1910's versions of the 3 EQUIVALENT shared files did **not** revert any of our reductions (the reductions live in files #1910 never touched, or were re-applied on top).

| Reduction | Verdict | Evidence |
|-----------|---------|----------|
| **#1904 `lanes/_git.py` consolidation** — `branch_exists`/`ref_exists` exist | **PRESENT** | `src/specify_cli/lanes/_git.py:40` (`branch_exists` → `refs/heads/<b>`), `:49` (`ref_exists` → `<ref>^{commit}`), both delegating to a single private `_verify`. |
| → call-site `coordination/status_transition.py` delegates | **PRESENT** | `:25` `from ...lanes._git import branch_exists as _branch_exists`; used `:93`, `:445`. No inline `rev-parse` for branch existence. |
| → call-site `missions/_create.py` delegates | **PRESENT** | `:46` `branch_exists`, `:47` `ref_exists as _ref_resolves`; called `:206` and `:199`. |
| → call-site `lanes/worktree_allocator.py` delegates | **PRESENT** | `:27` import; `:259`, `:339`, `:375` delegate. |
| → call-site `lanes/merge.py` delegates | **PRESENT** | `:25` `import branch_exists as _shared_branch_exists`; thin wrapper `:247–251` routes through it while preserving `_make_merge_env` single env authority (explicit `#1904` rationale comment). NOT reverted to inline. |
| **Boy-scout: doctrine.py `_JSON_*` const** | **PRESENT** | `cli/commands/doctrine.py:51` `_JSON_OPTION_HELP`, reused `:204`, `:303`. |
| **Boy-scout: sync/daemon.py `_HEALTH_*` const** | **PRESENT** | `sync/daemon.py:126` `_HEALTH_ENDPOINT_PATH`, `:138` `_STARTUP_HEALTH_TIMEOUT_SECONDS`, used `:286`. |
| **Boy-scout: sync/owner.py helpers** | **PRESENT** | `sync/owner.py:61,159,214,220,311` (`_canonical_executable_path`, `_owner_dir`, `_optional_str`, `_record_from_mapping`, `_resolve_source_checkout_path`). |
| **Boy-scout: drg/validator.py split** | **PRESENT** | Canonical source at `src/doctrine/drg/validator.py` (not `src/specify_cli/...`). File present. |
| **Boy-scout: org_charter.py helpers** | **PRESENT** | Canonical file is `src/specify_cli/doctrine/org_charter.py` (prompt path was approximate). Present. |
| **Boy-scout: agent/workflow.py `_enforce_*`** | **PRESENT** | `cli/commands/agent/workflow.py:132` `_enforce_bulk_edit_diff_compliance`, called `:2261`. |
| **Boy-scout: upgrade.py `_print_upgrade_section`** | **PRESENT** | `cli/commands/upgrade.py:962`, reused `:998`, `:1001`. |
| **Boy-scout: core/worktree.py helpers** | **PRESENT** | `core/worktree.py:35,109,243,264` (`_ensure_spec_kitty_exclude`, `_exclude_from_git`, `_existing_worktree_is_valid`, `_create_workspace_with_fallback`). |
| **Boy-scout: _read_path_resolver.py helper** | **PRESENT** | `missions/_read_path_resolver.py:90,102,130,171` helpers (`_declares_coordination_branch`, `_compose_mission_dir`, etc.). |
| **FR-007 `resolve_transaction_mid8`** in branch_naming | **PRESENT** | `lanes/branch_naming.py:235` def, `:41` in `__all__`. |
| → consumer `status_transition.py` routes through it | **PRESENT** | `:26` import, `:260` `effective_mid8 = resolve_transaction_mid8(...)`. |
| → consumer `implement.py` routes through it | **PRESENT** | `:395` import, `:397` call (in `_resolve_bookkeeping_transaction_identifiers`). |
| → `"00000000"` fabrication idiom removed | **PRESENT (gone)** | Zero hits for `00000000` across `branch_naming.py`, `implement.py`, `status_transition.py`. |
| **SonarCloud: recovery.py redundant-except** | **PRESENT** | `lanes/recovery.py:240` `except (OSError, ValueError):` with subset-rationale comment (`FileNotFoundError ⊂ OSError; json.JSONDecodeError ⊂ ValueError`) — the redundant nested except was collapsed. |
| **SonarCloud: _substantive.py reluctant→non-backtracking** | **PRESENT** | `missions/_substantive.py:171,173` value captures use `[^\n]*` (line-bounded, non-backtracking) with explicit NOTE explaining `[ \t]*` over `\s*` to prevent newline leak. No `.*?` reluctant quantifier in the technical-context scan. |

**Section verdict: CLEAN.** Every named reduction is present in reduced form; none was silently reverted by take-theirs.

---

## 2. Phantom / dead-code — new public symbols vs live non-test callers

Every audited symbol has at least one **live production (non-test) caller**. No phantoms.

| Symbol | Live production caller(s) | Verdict |
|--------|---------------------------|---------|
| `WorktreeTopology` | `status/emit.py:398,414`; `status/work_package_lifecycle.py:67,83` | LIVE |
| `classify_worktree_topology` | `status/emit.py:399,411`; `status/work_package_lifecycle.py:68,80` | LIVE |
| `is_registered_coord_worktree` | `workspace/root_resolver.py:68,85`; `status/aggregate.py:291,294` | LIVE |
| `read_worktree_registry` | `surface_resolver.py:268`; `dashboard/scanner.py:317,331` | LIVE |
| `is_under_worktrees_segment` | `status/aggregate.py:344,354`; `coordination/status_service.py:66,68` | LIVE |
| `CoordinationBranchDeleted` | raised `surface_resolver.py:526` on the live `classify_worktree_topology` path (R3); subclass of `StatusReadPathNotFound` → caught transitively by existing handlers | LIVE (transitive-except, per prompt-accepted) |
| `mission_branch_name_required` | `status/aggregate.py:689,691`; `lanes/recovery.py:23,259` | LIVE |
| `BranchIdentityUnresolved` | raised `branch_naming.py:232,327`; re-raised w/ enrichment `lanes/recovery.py:262,265` | LIVE |
| `resolve_transaction_mid8` | `status_transition.py:260`; `implement.py:397` | LIVE |
| `branch_exists` | `status_transition.py:93,445`; `_create.py:206`; `worktree_allocator.py:259,339,375`; `merge.py:251` | LIVE |
| `ref_exists` | `_create.py:199` (as `_ref_resolves`) | LIVE |
| `describe_technical_context_gap` | `cli/commands/agent/mission.py:2187,2189` (plan-gap blocked-reason wiring) | LIVE |
| `_resolve_path_ref` | `doctrine/drg/migration/extractor.py:577,614` | LIVE |
| `DependencyLaneMergeConflictError` | raised `worktree_allocator.py:299` | LIVE |
| `_merge_dependency_lane_tips` | `worktree_allocator.py:136,176` | LIVE |

**Section verdict: CLEAN.** Zero phantom symbols. The FR-013 `describe_technical_context_gap` and FR-007 `resolve_transaction_mid8` — the two re-applied-on-top survivors most at risk of losing their wiring in the reconcile — both retain their production call-sites.

---

## 3. Duplication reintroduced by the reconcile

Investigated whether taking #1910's shared files (`runtime_bridge.py`, `acceptance/__init__.py`, `_substantive.py`) reintroduced an existence/coord helper duplicating `lanes/_git.branch_exists`/`ref_exists` or the `surface_resolver` predicates.

**Finding: NO duplication reintroduced by the reconcile.**

Idioms that look like duplicates, traced to provenance:

| Helper | Idiom | Provenance | Duplication? |
|--------|-------|------------|--------------|
| `acceptance/__init__.py:873` `_git_ref_exists` | `rev-parse --verify --quiet` | **Pre-existing — commit `742b7abcf` (#1273)**, far predates #1904/#1908/#1910. Not introduced or re-added by the reconcile. | NO (pre-existing out-of-scope; LOW pre-existing debt, not a regression) |
| `lanes/lifecycle_sync.py:68` `_git_ref_exists` | rev-parse | **Pre-existing — commit `8ad6bb400`** ("sync lane state after coordination commits"). | NO (pre-existing) |
| `git/commit_helpers.py:643` `_destination_ref_exists` | rev-parse | Pre-existing helper in the commit pipeline. | NO (pre-existing) |
| `coordination/surface_resolver.py:302` `_coord_branch_exists` | `rev-parse --git-dir` + ref check | **Ours (the seam).** Intentionally NOT delegated to `_git.branch_exists`: distinct fail-closed semantics — treats branch as PRESENT when `repo_root` is unreadable / not-a-git-repo (so R3 is never falsely fired from a non-repo tmp dir), whereas `_git.branch_exists` returns False. Different contract, justified distinct helper. | NO (semantically distinct, documented) |
| `missions/_substantive.py:311,327` `cat-file -e` (coord-ref + HEAD) | inline `cat-file -e` | **Theirs (#1910), take-theirs.** This is the coordination-*branch-ref content* check inside `is_committed(..., placement=...)` — an artifact-committedness probe, NOT a branch/ref-existence classifier. No overlap with `_git`'s `branch_exists`/`ref_exists` (which answer "does the ref exist", not "is this file present at that ref"). | NO (distinct concern) |

`#1910`'s `runtime_bridge.py` carries no branch/ref-existence or coord-classify helper that rivals `_git` or the `surface_resolver` predicates — its helpers (`_resolve_coordination_branch`, `_mission_declares_coordination_branch`, …) are mission-resolution wrappers, not existence primitives.

Crucially: there is **no copy of any #1904-consolidated symbol** in #1910's diff, and #1910 did **not** reintroduce a `rev-parse --verify` / `cat-file -e` existence idiom in any file #1904 had unified. The only `rev-parse --verify` hits outside `_git.py` are (a) docstring mentions and (b) the pre-existing/semantically-distinct helpers above.

**Section verdict: CLEAN (reconcile-induced).** One **LOW pre-existing** observation: `acceptance._git_ref_exists`, `lifecycle_sync._git_ref_exists`, and `commit_helpers._destination_ref_exists` are three near-identical pre-existing private ref-existence helpers that *could* be unified onto `lanes/_git.ref_exists` — but this debt predates this mission and #1904 (whose scope was the 4 branch-existence call-sites), so it is **out of scope** and **not a reconcile regression**. Recommend a separate follow-up ticket if a future #1904-style sweep is desired; do NOT fold into this mission.

---

## 4. Ratchets / boundary suites

| Suite | Result |
|-------|--------|
| `tests/architectural/test_no_dead_symbols.py` | **GREEN** (1 passed, 2.30s) |
| `tests/architectural/test_topology_resolution_boundary.py` | **GREEN** (3 passed) |
| `tests/architectural/test_shared_package_boundary.py` | **GREEN** (8 passed) |
| `tests/architectural/test_no_legacy_terminology.py` | **GREEN** (2 passed) |

No new dead-symbol allowlist drift. The overlap-map's planned manual re-apply of our `_CATEGORY_C_WP_IN_FLIGHT_TOPOLOGY_AUTHORITY` allowlist block on top of #1910's grandfathered-entry removal landed cleanly (ratchet green confirms the allowlist matches live reality — no over-grandfathering).

---

## Overall verdict

**Reductions intact + no phantom/duplicate code: YES.**

- All #1904 / boy-scout / FR-007 / SonarCloud reductions survived the take-theirs collision in reduced form (Section 1: CLEAN).
- All 15 audited new public symbols have live production callers — zero phantoms (Section 2: CLEAN).
- The reconcile reintroduced no duplicate existence/coord helper; the EQUIVALENT take-theirs files carry only distinct-concern idioms (Section 3: CLEAN re reconcile).
- All four ratchet/boundary suites GREEN (Section 4).

### Remediation list (none blocking; do NOT apply here)

1. **LOW (pre-existing, out-of-scope):** Three near-identical private ref-existence helpers — `acceptance.__init__._git_ref_exists`, `lanes.lifecycle_sync._git_ref_exists`, `git.commit_helpers._destination_ref_exists` — duplicate the contract of `lanes/_git.ref_exists`. They predate #1904 and this mission. *Recommendation:* file a follow-up "extend #1904 sweep to ref-existence helpers" ticket; explicitly do not expand this mission's scope. (`_coord_branch_exists` is deliberately excluded — distinct fail-closed contract.)

No HIGH/BLOCKING findings.
