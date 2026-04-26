# Phase 0 Research — Stability & Hygiene Hardening

**Mission**: `stability-and-hygiene-hardening-2026-04-01KQ4ARB`
**Date**: 2026-04-26
**Inputs**: `spec.md`, `plan.md`, `start-here.md`, `CLAUDE.md` (project root).

This document fulfills DIRECTIVE_003 (Decision Documentation). Each section
records a decision, its rationale, and the alternatives considered. Premortem
and FR → test mapping appear at the end.

---

## D1. Issue traceability shape

**Decision**: A single `issue-matrix.md` file is produced as part of
`/spec-kitty.tasks` (alongside the WP files) and lives at
`kitty-specs/<mission>/issue-matrix.md`. It is a Markdown table with one row
per GitHub issue listed in `start-here.md`. Columns: `repo`, `issue#`, `theme`,
`verdict`, `wp_id`, `evidence_ref`. Verdict ∈ {`fixed`,
`verified-already-fixed`, `deferred-with-followup`}. `evidence_ref` is a test
name, commit SHA, doc anchor, or new follow-up issue link.

**Rationale**: Single source of truth, machine-checkable in mission-review,
matches the existing pattern of mission artifacts living alongside `spec.md`.

**Alternatives considered**:
- A YAML file under `.kittify/traceability/`. Rejected — operator surface is
  Markdown; review skill reads Markdown; YAML would add a second source of
  truth.
- Inline in each WP file. Rejected — would duplicate rows when issues span
  WPs and would make mission-level rollups awkward.

---

## D2. `spec-kitty next` bare-call semantics (FR-019, FR-020)

**Decision**: A bare `spec-kitty next --agent <name> --mission <handle>` (no
`--result`) MUST return the next decision based on current state without
advancing. Prior `--result` defaulting was a coupling bug: the runtime treated
"no result" as an implicit "previous step succeeded". The fix is two-fold:

1. The CLI bridge sets `result=None` when the flag is absent and passes that
   through to the runtime. The runtime's "advance" logic only fires on
   `result == 'success'`. `result is None` is a *query*, not an outcome.
2. When the runtime cannot determine a next decision, it emits a structured
   error decision (`kind="blocked"`, `reason=<concrete validation message>`,
   `mission_state` set to the actual current state, never `unknown`). The
   `[QUERY - no result provided]` placeholder is removed from the prompt
   templates.

**Rationale**: Aligns with the documented decision algorithm (the runtime is a
state machine; outcomes are explicit). Eliminates an entire class of "the
runtime advanced when I just wanted to look".

**Alternatives considered**:
- Make the bare call an error. Rejected — agents legitimately call `next` to
  inspect; making this an error breaks documented loops.
- Default to `result=blocked`. Rejected — also lies; the previous step might
  have succeeded.

---

## D3. `mark-status` ↔ `tasks-finalize` shape mismatch (FR-017)

**Decision**: `mark-status` is extended to accept either bare WP IDs (`WP01`)
or the qualified shape that `tasks-finalize` emits (e.g.
`<mission_slug>/WP01`). Both are normalized to the WP ID before the
transition is validated. The contract test in
`tests/contract/test_mark_status_input_shapes.py` enforces both shapes.

**Rationale**: Backwards-compatible, no breaking change for either side, gets
the parser-vs-emitter contract under test.

**Alternatives considered**:
- Change `tasks-finalize` to emit bare WP IDs. Rejected — emitted by a
  command other agents may parse; changing the emitter is a bigger blast
  radius than extending the parser.

---

## D4. Planning-artifact WP execution (FR-015)

**Decision**: A WP that produces only planning artifacts (no source-code
changes) is marked in its frontmatter as
`execution_mode: planning_artifact`. The runtime treats this mode as
"non-worktree": no lane allocation, no worktree path. The WP's status events
reference the canonical mission repo as workspace. The lane planner does not
include planning-artifact WPs in lane fan-out. The runtime's decision JSON for
such a WP includes `workspace_path: null` and a free-form `notes` field
explaining how to execute.

**Rationale**: Planning-artifact WPs (e.g. WP08's traceability matrix update,
research notes, ADRs) do not benefit from a worktree. Forcing one creates the
silent-failure mode where allocation fails and the WP appears blocked.

**Alternatives considered**:
- Always allocate a worktree. Rejected — wasteful and prone to the failure
  mode described.
- Drop the mode and require all WPs to touch source. Rejected — narrows the
  WP shape and makes the mission system less general.

---

## D5. Worktree → canonical repo writes (FR-013)

**Decision**: A new `workspace/root_resolver.py` exposes
`resolve_canonical_root(cwd: Path) -> Path` that walks up to find the worktree
parent (`.git/worktrees/<name>` → `commondir`) and returns the main repo
path. Status emit, charter writes, and config writes call this resolver
exactly once per command invocation and pass the result down. The contract
test in `tests/contract/test_canonical_root_when_in_worktree.py` simulates a
worktree CWD and asserts that emitted events land in the canonical
`kitty-specs/<slug>/status.events.jsonl`.

**Rationale**: One place to resolve, one place to test, no per-call ad-hoc
canonicalisation.

**Alternatives considered**:
- Have each emitter resolve independently. Rejected — duplicated logic and
  the existing bug already shows the cost.

---

## D6. Intake escape and size cap (FR-007, FR-008, FR-009)

**Decision**:
- **Provenance escape**: provenance lines that mention `source_file:` are
  written through a single helper that strips control characters, escapes
  comment-terminating substrings (`-->`, `*/`, `#` at line start), and clips
  to 256 bytes.
- **Symlink / traversal**: the scanner uses `Path.resolve(strict=True)` and
  asserts `resolved.is_relative_to(intake_root_resolved)`. Symlinks that
  escape the root cause a structured `INTAKE_PATH_ESCAPE` error. The check
  happens *before* the file is opened.
- **Size cap**: a fixed default cap of 5 MB (configurable in
  `.kittify/config.yaml` via `intake.max_brief_bytes`). The cap is enforced by
  `os.stat()` before opening; if `os.stat()` is unavailable (e.g. STDIN), the
  reader uses `read1(cap+1)` and fails fast at `cap+1` bytes.

**Rationale**: Defense in depth at the boundary; cheap; testable in
isolation. Memory growth (NFR-003) is bounded to `cap + small overhead`.

**Alternatives considered**:
- Stream-and-truncate without erroring. Rejected — silently truncated briefs
  would be worse than rejection.
- Sandbox the intake reader. Rejected — over-engineering for a tool intended
  to run on operator laptops.

---

## D7. Atomic intake write (FR-010, NFR-004)

**Decision**: Brief and provenance writes use the existing `safe_commit`
pattern: write to `<target>.tmp`, fsync, then `os.replace(<tmp>, <target>)`.
Same filesystem is required (default; same directory). A test under
`tests/integration/test_intake_atomic_writes.py` simulates kill-9 mid-write
across 100 trials and asserts no `<target>` files remain in a half-written
state.

**Rationale**: Battle-tested pattern already in the repo for status events
(see `src/specify_cli/git/safe_commit`). No new dependency.

**Alternatives considered**:
- File locking. Rejected — atomic rename is sufficient and simpler.

---

## D8. Contract test ↔ resolved version pinning (FR-022)

**Decision**: A new contract test
(`tests/contract/test_events_envelope_matches_resolved_version.py`) reads the
resolved version of `spec-kitty-events` from `uv.lock` (via
`tomllib`) and asserts that the envelope shape under test matches the public
schema for that exact version. If `uv.lock` is missing in CI (e.g. someone
imports the test in a venv without lockfile), the test fails with a clear
diagnostic. Bumping `spec-kitty-events` requires updating the snapshot
shipped under `tests/contract/snapshots/spec-kitty-events-<version>.json`,
which is auto-generated by a `scripts/snapshot_events_envelope.py`.

**Rationale**: The drift this prevents is exactly the bug the issue tracker
records. The lock file is already canonical for resolved versions; reading it
in tests avoids a parallel source of truth.

**Alternatives considered**:
- Hardcode an expected version in the test. Rejected — every bump would
  require a test edit instead of a snapshot regen.

---

## D9. Centralized auth transport (FR-030)

**Decision**: A new module `src/specify_cli/auth/transport.py` exposes a
single `AuthenticatedClient` class wrapping `httpx.Client` with:

- one `TokenStore` (in-process; reads `.kittify/auth/credentials.json`).
- one `RefreshLock` (mutex around refresh; coalesces concurrent 401 → refresh
  → retry).
- one structured-failure surface (`AuthRefreshFailed` with cause chain).

`sync`, `tracker`, and `websocket` clients import this client. They do not
implement their own refresh. A new architectural test
(`tests/architectural/test_auth_transport_singleton.py`) asserts that no
caller in those subsystems references `httpx.Client` or `httpx.AsyncClient`
directly outside `auth/transport.py`.

**Rationale**: One refresh, one log line, one place to fix when the auth flow
changes.

**Alternatives considered**:
- Continue with per-client refresh. Rejected — that is the existing bug.
- Move to a third-party auth library. Rejected — introduces new dependency
  and the existing httpx-based stack is sufficient.

---

## D10. Offline queue overflow (FR-027)

**Decision**: When `OfflineQueue.append()` would exceed
`sync.queue_max_events` (default 10_000), it raises a structured
`OfflineQueueFull` exception. The CLI surface catches it and:

1. Prints a single recoverable line to stderr explaining the condition.
2. Offers to drain to a `.kittify/sync/overflow-<utc-iso>.jsonl` file
   (operator confirms or `--auto-drain` flag).
3. Exits non-zero unless drained.

A test under `tests/integration/test_offline_queue_overflow.py` asserts that
no event is silently dropped and that the drained file is replayable.

**Rationale**: Loud, recoverable, and observable.

**Alternatives considered**:
- Drop oldest. Rejected — the lost events are exactly what the operator
  needs.
- Auto-grow without limit. Rejected — disk-fill DoS.

---

## D11. Replay tenant collision (FR-028)

**Decision**: `sync.replay()` consults `(tenant_id, project_id)` on each
incoming event. If both match local target → idempotent apply. If `tenant_id`
mismatches → raise structured `TenantMismatch` and skip; log the conflict.
If `tenant_id` matches but `project_id` mismatches → raise structured
`ProjectMismatch` and skip. A test fixture provides paired event streams to
exercise both surfaces.

**Rationale**: Deterministic, structured, no silent merge.

**Alternatives considered**:
- Force-merge on collision. Rejected — data corruption risk.

---

## D12. Token-refresh log dedup (FR-029, NFR-007)

**Decision**: `AuthenticatedClient` keeps a `_user_facing_failure_emitted`
boolean per command invocation. The first refresh failure prints once; later
failures within the same invocation are accumulated to a debug log only.
The boolean resets on next command invocation.

**Rationale**: Bounded user-facing noise; full debug trail still available.

**Alternatives considered**:
- Per-call rate-limit. Rejected — coarser; one-line cap is the operator
  promise.

---

## D13. Charter compact-mode fidelity (FR-034)

**Decision**: The compact view now includes an additional "Section Anchors"
block listing every charter section heading that the bootstrap view would
include, even when the body is omitted in compact mode. Compact mode also
preserves all directive IDs (e.g. DIRECTIVE_003) and tactic IDs verbatim;
only the long-form prose body is collapsed. A contract test
(`tests/contract/test_charter_compact_includes_section_anchors.py`) asserts
that for each fixture charter, the compact view's directive list and section
anchor list equal the bootstrap view's.

**Rationale**: Agents follow rules by ID; losing IDs in compact mode is the
exact failure path issue #790 describes.

**Alternatives considered**:
- Drop compact mode altogether. Rejected — defeats the purpose of action
  scoping; regressions on token budget.

---

## D14. Fail-loud uninitialized repo (FR-032)

**Decision**: At the top of `specify`, `plan`, and `tasks` commands, the CLI
calls `workspace.assert_initialized()` which checks for `.kittify/config.yaml`
and `kitty-specs/` in the canonical root. If absent, raises
`SpecKittyNotInitialized` with the resolved root path and an actionable
message. There is **no** fallback to a parent directory or a sibling
initialized repo. A regression test under
`tests/integration/test_fail_loud_uninitialized_repo.py` builds a temp tree
and runs each command, asserting non-zero exit and no file writes outside the
temp dir.

**Rationale**: Symmetric with FR-005 (loud failure beats silent fallback);
matches existing C-007 stance on no-silent-fallback selectors.

---

## D15. Branch-strategy gate for PR-bound missions (FR-033)

**Decision**: When `mission create` is invoked while CWD is on
`merge_target_branch` AND `meta.json` declares the mission as PR-bound (a new
`pr_bound: true` field set by intake or operator), the CLI prompts the
operator to confirm or to switch to a feature branch. The prompt is
suppressed by `--branch-strategy already-confirmed` for scripted use. A
regression test under
`tests/integration/test_branch_strategy_gate.py` asserts the prompt fires.

**Rationale**: Captures the intent of issue #765 / #787 without forbidding
mission creation on `main` (which is the standard flow for non-PR-bound
spec-kitty work).

---

## D16. Hidden legacy `--feature` aliases (FR-035)

**Decision**: All Typer commands that previously accepted `--feature` keep it
as a hidden option (`hidden=True` in Typer). Help output for the commands
shows only `--mission`. A test under
`tests/integration/test_legacy_feature_alias.py` asserts that `--feature`
still works on the canonical command set.

---

## D17. Local custom mission loader post-merge hygiene (FR-036)

**Decision**: Audit the post-merge code path that handles the local custom
mission loader (issue #801). If the audit finds the cleanup is complete on
`main`, file a regression test that would have failed pre-fix and close
#801 as `verified-already-fixed`. If the audit finds gaps, scope a narrow
fix into WP07 and document the remaining work as a follow-up issue.

---

## D18. `spec-kitty-runtime` retirement verification (FR-025, C-003)

**Decision**: Add an architectural test
(`tests/architectural/test_no_runtime_pypi_dep.py`) that:

1. Asserts `pyproject.toml` does not declare `spec-kitty-runtime` as a
   dependency.
2. Imports `spec-kitty next` machinery from `_internal_runtime` and asserts
   `import spec_kitty_runtime` is **not** required for `spec-kitty next` to
   resolve a basic decision.

The clean-install verification job in `.github/workflows/ci-quality.yml`
already covers the venv-level claim; this test makes the claim
fail-on-regression at unit-test time.

---

## Premortem (failure modes deliberately considered)

| Risk | Mitigation |
|------|------------|
| Merge resume corrupts state if interrupted twice | All state writes use atomic rename; `.kittify/merge-state.json` includes a monotonic `started_at` so double-resume is detectable |
| Contract test pinning to `uv.lock` breaks dev installs that use `pip`-only flow | Test reads `uv.lock` if present; falls back to importlib metadata; documents in `docs/development/local-overrides.md` |
| Centralized auth transport refactor regresses sync throughput | New transport is a thin wrapper around the same httpx primitives; benchmark snapshot in test asserts throughput within 10% of baseline |
| E2E gate slows down mission review unbearably | NFR-006 caps the suite at 20 min; expensive scenarios are tagged so reviewers can run a smoke subset locally and the full set in CI |
| Contract pinning forces a flood of test churn on every events bump | Snapshot file is auto-generated via `scripts/snapshot_events_envelope.py`; bumping events is a 2-step (`update` → `snapshot`) workflow |
| Charter compact fix accidentally bloats compact view tokens | Compact view body remains short; only section-anchor + directive-ID list added; smoke test asserts compact ≤ N tokens |
| Brief-write atomic rename across filesystems silently degrades to non-atomic | Helper checks that `<tmp>` and `<target>` share a device; logs and falls back loudly if not |
| Sync overflow drain creates many small files | Drain file uses UTC-stamped suffix; operators rotate via standard cron / `find -mtime` patterns; no auto-cleanup to avoid hiding evidence |
| Fail-loud uninitialized repo breaks scripted CI invocations on monorepos | Error includes a `--repo-root <path>` hint; documented in migration runbook |
| Legacy `--feature` hide breaks existing aliases | Hidden, not removed; integration test pins behavior |

---

## FR → test mapping

| FR | Primary test file | Layer |
|----|-------------------|-------|
| FR-001 | tests/integration/test_merge_lane_planning_data_loss.py | integration |
| FR-002 | tests/integration/test_merge_resume.py | integration |
| FR-003 | tests/integration/test_post_merge_index_refresh.py | integration |
| FR-004 | tests/integration/test_post_merge_unrelated_untracked.py | integration |
| FR-005 | tests/unit/lanes/test_dependent_wp_scheduling.py | unit |
| FR-006 | tests/integration/test_lane_db_isolation.py | integration |
| FR-007 | tests/unit/intake/test_provenance_escape.py | unit |
| FR-008 | tests/unit/intake/test_traversal_symlink_block.py | unit |
| FR-009 | tests/integration/test_intake_size_cap.py | integration |
| FR-010 | tests/integration/test_intake_atomic_writes.py | integration |
| FR-011 | tests/unit/intake/test_missing_vs_corrupt.py | unit |
| FR-012 | tests/unit/intake/test_root_consistency.py | unit |
| FR-013 | tests/contract/test_canonical_root_when_in_worktree.py | contract |
| FR-014 | tests/integration/test_status_emit_on_alloc_failure.py | integration |
| FR-015 | tests/integration/test_planning_artifact_wp.py | integration |
| FR-016 | tests/unit/status/test_review_claim_transition.py | unit |
| FR-017 | tests/contract/test_mark_status_input_shapes.py | contract |
| FR-018 | tests/integration/test_dashboard_counters.py | integration |
| FR-019 | tests/integration/test_next_no_implicit_success.py | integration |
| FR-020 | tests/integration/test_next_no_unknown_state.py | integration |
| FR-021 | tests/contract/test_plan_mission_yaml_validates.py | contract |
| FR-022 | tests/contract/test_events_envelope_matches_resolved_version.py | contract |
| FR-023 | tests/integration/test_mission_review_contract_gate.py | integration |
| FR-024 | tests/architectural/test_events_tracker_public_imports.py | architectural |
| FR-025 | tests/architectural/test_no_runtime_pypi_dep.py | architectural |
| FR-026 | tests/integration/test_release_gate_downstream_consumer.py | integration |
| FR-027 | tests/integration/test_offline_queue_overflow.py | integration |
| FR-028 | tests/integration/test_replay_tenant_collision.py | integration |
| FR-029 | tests/integration/test_token_refresh_dedup.py | integration |
| FR-030 | tests/architectural/test_auth_transport_singleton.py | architectural |
| FR-031 | tests/integration/test_tracker_bidirectional_retry.py | integration |
| FR-032 | tests/integration/test_fail_loud_uninitialized_repo.py | integration |
| FR-033 | tests/integration/test_branch_strategy_gate.py | integration |
| FR-034 | tests/contract/test_charter_compact_includes_section_anchors.py | contract |
| FR-035 | tests/integration/test_legacy_feature_alias.py | integration |
| FR-036 | tests/integration/test_post_merge_custom_mission_loader.py | integration |
| FR-037 | mission-review skill verifies issue-matrix.md | review |
| FR-038 | spec-kitty-end-to-end-testing/scenarios/dependent_wp_planning_lane.py | e2e |
| FR-039 | spec-kitty-end-to-end-testing/scenarios/uninitialized_repo_fail_loud.py | e2e |
| FR-040 | spec-kitty-end-to-end-testing/scenarios/saas_sync_enabled.py | e2e |
| FR-041 | spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py | e2e |

---

## ADR seeds

The following ADRs are scaffolded during implementation; final ADR text is
authored within the owning WP:

- ADR-2026-04-26-1: Contract-test → resolved-version pinning (WP05).
- ADR-2026-04-26-2: Centralized auth transport boundary (WP06).
- ADR-2026-04-26-3: Cross-repo e2e as hard mission-review gate (WP08).

ADRs land in `architecture/2.x/adr/` and are referenced from `research.md`,
`tasks.md`, and the affected WP files.
