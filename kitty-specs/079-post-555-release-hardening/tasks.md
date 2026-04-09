# Tasks: 3.1.1 Post-555 Release Hardening

**Mission**: `079-post-555-release-hardening`
**Branch contract**: planning_base = `main` · merge_target = `main`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Created**: 2026-04-09T07:30:50Z
**Working repo**: `/private/tmp/311/spec-kitty`

---

## Summary

Seven parallel work packages that close the forward-correctness gaps blocking `3.1.1` after PR #555. The packages are independent of each other (WP01–WP06) and can all run concurrently. WP07 (version coherence + dogfood acceptance) is the only sequential gate — it depends on all prior WPs and verifies the complete release state.

Each WP traces directly to a spec track (§7 of `spec.md`) and its corresponding plan design notes (§6 of `plan.md`).

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|---------:|
| T001 | Remove `git init`/commit call path from `init.py`; remove `--no-git` flag | WP01 | [P] | [D] | [D] | [D] |
| T002 | Remove `.agents/skills/` seeding from `init.py` | WP01 | [D] |
| T003 | Rewrite `init` next-steps output (name `spec-kitty next` + agent action verbs) | WP01 | [D] |
| T004 | Add idempotency check on re-run (fail-fast or no-op) | WP01 | [D] |
| T005 | Update `init --help` text to describe the new model accurately | WP01 | [D] |
| T006 | Regression tests for Track 1 (T1.1–T1.7 from test-contracts.md) | WP01 | [D] |
| T007 | Bound `_split_wp_sections()` at top-level non-WP `##` headings | WP02 | [D] |
| T008 | Document explicit-dependencies-only invariant in parser docstring | WP02 | [D] |
| T009 | Regression tests for Track 4 (T4.1, T4.3, T4.4 + all 21 existing tests still pass) | WP02 | [D] |
| T010 | Stop filtering `PLANNING_ARTIFACT` in `compute.py`; assign to `lane-planning` | WP03 | [D] |
| T011 | Update `branch_naming.py`: `lane_branch_name(..., "lane-planning")` → planning branch | WP03 | [D] |
| T012 | `worktree.py` + `workspace_context.py`: route `lane-planning` → main repo checkout; add `get_next_feature_number` display-only docstring | WP03 | [D] |
| T013 | Collapse `resolver.py:174-182` `execution_mode` special-case | WP03 | [D] |
| T014 | `implement.py`: uniform lane lookup + rewrite `--help` docstring as internal-infrastructure | WP03 | [D] |
| T015 | Regression tests for Track 2 (T2.1–T2.6 from test-contracts.md) | WP03 | [D] |
| T016 | Mint ULID `mission_id` in `mission_creation.py`; persist to `meta.json`; lock write; mint 079's own `mission_id` | WP04 | [D] |
| T017 | Add `mission_id` to `MissionIdentity` dataclass; update `resolve_mission_identity()` | WP04 | [D] |
| T018 | Add `mission_id` to `emit_mission_created()` payload in `events.py` + `emitter.py` | WP04 | [D] |
| T019 | Regression tests for Track 3 (T3.1–T3.6 from test-contracts.md) | WP04 | [D] |
| T020 | Extend `FileLock` scope in `refresh_tokens()` to full read→network→persist transaction | WP05 | [D] |
| T021 | Re-read-on-401 path: stale 401 exits cleanly; real 401 clears under lock | WP05 | [D] |
| T022 | Verify httpx timeout < 10s lock timeout; set explicit timeout if not | WP05 | [D] |
| T023 | Regression tests for Track 5 (T5.1–T5.4 from test-contracts.md) | WP05 | [D] |
| T024 | Update `README.md` canonical workflow line + mermaid diagram | WP06 | [D] |
| T025 | Update slash-command source templates (replace `spec-kitty implement WP##` with `spec-kitty agent action implement`) | WP06 | [D] |
| T026 | Update `docs/` canonical-path mentions in first ~5 paragraphs of ~12 files | WP06 | [D] |
| T027 | Regression tests for Track 6 (T6.1, T6.2, T6.4, T6.5 from test-contracts.md) | WP06 | [D] |
| T028 | Bump `.kittify/metadata.yaml` version to match `pyproject.toml` | WP07 | — | [D] |
| T029 | Add `validate_metadata_yaml_version_sync()` to `scripts/release/validate_release.py` | WP07 | — | [D] |
| T030 | Verify CHANGELOG-presence check runs in branch mode; verify structured draft artifact | WP07 | — | [D] |
| T031 | Regression tests for Track 7 (T7.1–T7.4 from test-contracts.md) | WP07 | — | [D] |
| T032 | Dogfood acceptance: run quickstart V-7 walkthrough; verify all RG-1..RG-8 gates pass | WP07 | — | [D] |

**Total**: 32 subtasks across 7 WPs · Average 4.6 subtasks/WP · All within 3–7 ideal range

---

## WP01 — Track 1: Init Coherence

**Goal**: Rewrite `spec-kitty init` so it is file-creation-only with no git side effects, no `.agents/skills/` seeding, and accurate next-step guidance naming `spec-kitty next` and `spec-kitty agent action implement/review` as the canonical user workflow.

**Priority**: P1 — first in rollout sequence; every other track's verification relies on a coherent fresh `init`.

**Spec FRs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008

**Subtasks**:
- [ ] T001 Remove `git init`/commit call path; remove `--no-git` flag (WP01)
- [ ] T002 Remove `.agents/skills/` seeding from `init.py` (WP01)
- [ ] T003 Rewrite `init` next-steps output text (WP01)
- [ ] T004 Add idempotency check on re-run (WP01)
- [ ] T005 Update `init --help` text (WP01)
- [ ] T006 Regression tests for Track 1 (WP01)

**Key technical notes**:
- The `--no-git` flag is **removed entirely** (not converted to a no-op). Users passing it get a typer "no such option" error. This is intentional and documented in D-1.
- `init_git_repo()` call path is removed from `init.py`. The function itself may remain in `git_ops.py` if other callers exist; note them in the PR description.
- Next-steps text: `spec-kitty next --agent <agent> --mission <slug>` (loop entry) + `spec-kitty agent action implement` / `spec-kitty agent action review` (per-decision verbs). Do NOT name `spec-kitty implement` anywhere in user-visible output.
- The literal string `"Initial commit from Specify template"` must be absent from `src/` after this WP.

**Dependencies**: none
**Estimated prompt size**: ~380 lines
**Prompt file**: [tasks/WP01-init-coherence.md](tasks/WP01-init-coherence.md)

---

## WP02 — Track 4: Dependency Parser Hotfix

**Goal**: Bound `_split_wp_sections()` so the final WP section does not slurp trailing prose to EOF. Preserve all 21 existing parser tests. Add the FR-304 regression test.

**Priority**: P1 — land early so downstream finalize-tasks calls use the correct parser.

**Spec FRs**: FR-301, FR-302, FR-303, FR-304, FR-305

**Subtasks**:
- [ ] T007 Bound `_split_wp_sections()` at non-WP `##` headings (WP02)
- [ ] T008 Document explicit-dependencies-only invariant (WP02)
- [ ] T009 Regression tests for Track 4 (WP02)

**Key technical notes**:
- Current bug at `dependency_parser.py:56`: `end = ... else len(tasks_content)` slurps to EOF. The fix: also stop at `^## ` (top-level heading) whose text does not match the WP id pattern. Sub-headings `^### ` inside a WP section are preserved.
- Contrary to the issue description, the parser does NOT do prose inference. The false positive is explicit-format patterns (e.g. `Depends on WP01`) matching trailing prose that happens to say "Depends on WP01". The section bound fixes this.
- After the fix, all 21 existing tests in `tests/core/test_dependency_parser.py` must still pass.

**Dependencies**: none
**Estimated prompt size**: ~200 lines
**Prompt file**: [tasks/WP02-dependency-parser-hotfix.md](tasks/WP02-dependency-parser-hotfix.md)

---

## WP03 — Track 2: Planning Artifact Lane Unification

**Goal**: Make planning-artifact WPs first-class lane-owned entities. Assign them the canonical `lane-planning` lane. Collapse the `execution_mode == "planning_artifact"` special-case branches at every downstream consumer. `lane-planning` resolves to the main repo checkout, never to a `.worktrees/` directory.

**Priority**: P1 — closes a fundamental lane-contract hole.

**Spec FRs**: FR-101, FR-102, FR-103, FR-104, FR-105, FR-106

**Subtasks**:
- [ ] T010 Stop filtering `PLANNING_ARTIFACT` in `compute.py`; assign to `lane-planning` (WP03)
- [ ] T011 Update `branch_naming.py` for `lane-planning` (WP03)
- [ ] T012 `worktree.py` + `workspace_context.py`: route `lane-planning` → main checkout + display-only docstring (WP03)
- [ ] T013 Collapse `resolver.py:174-182` special-case (WP03)
- [ ] T014 `implement.py`: uniform lane lookup + internal-infrastructure `--help` docstring (WP03)
- [ ] T015 Regression tests for Track 2 (WP03)

**Key technical notes**:
- `lane-planning` is a real `ExecutionLane` with `lane_id = "lane-planning"`. Every WP with `execution_mode == PLANNING_ARTIFACT` goes into this lane.
- `branch_naming.lane_branch_name(mission_slug, "lane-planning")` → the mission's `target_branch` (e.g. `"main"`), NOT `"kitty/mission-<slug>-lane-planning"`.
- `LanesManifest.planning_artifact_wps` is kept as a **derived view** (backward-compat with historical manifests). Do NOT remove it; just mark it deprecated in the docstring and ensure it is derivable from `lanes`.
- Resolver change: the `if execution_mode == "planning_artifact": authoritative_ref = None` branch at lines 174-182 is removed. All WPs go through `lane_for_wp()` → `lane_branch_name()`.
- `implement.py` T014 also rewrites the `--help` docstring to mark the command as internal infrastructure (see plan §6 Track 6).

**Dependencies**: none (T007 from WP02 is independent; lane computation and dependency parsing are separate subsystems)
**Estimated prompt size**: ~430 lines
**Prompt file**: [tasks/WP03-planning-artifact-lane-unification.md](tasks/WP03-planning-artifact-lane-unification.md)

---

## WP04 — Track 3: Mission Identity Phase 1

**Goal**: Mint a ULID `mission_id` at mission-creation time and persist it to `meta.json`. Add `mission_id` to `MissionIdentity` and to `emit_mission_created()` payload. Mint 079's own `mission_id` as dogfood (the first WP in this track fixes this mission's own meta.json).

**Priority**: P1 — forward-correctness gate; every new mission created after this lands has an immutable canonical identity.

**Spec FRs**: FR-201, FR-202, FR-203, FR-204, FR-205, FR-206

**Subtasks**:
- [x] T016 Mint ULID `mission_id` in `mission_creation.py`; persist + lock; mint 079's own (WP04)
- [x] T017 `MissionIdentity.mission_id` field + `resolve_mission_identity()` update (WP04)
- [x] T018 `mission_id` in `emit_mission_created()` payload (WP04)
- [x] T019 Regression tests for Track 3 (WP04)

**Key technical notes**:
- `python-ulid` (≥3.0) is already in `pyproject.toml:72`. Use `from ulid import ULID; str(ULID())`.
- `mission_creation.py:create_mission_core()` gets `meta.setdefault("mission_id", str(ULID()))` alongside existing fields.
- The meta.json write should be wrapped in `filelock.FileLock` using the existing `feature_status_lock_path()` pattern from `status/locking.py`. This prevents partial writes under concurrent create.
- `MissionIdentity.mission_id: str | None = None` — the `None` default is the ONLY legacy-tolerance hook. New flows that depend on `mission_id` treat `None` as a hard error (raise, don't default).
- T016 also edits `kitty-specs/079-post-555-release-hardening/meta.json` directly to add a ULID for this mission itself. This is the first concrete dogfood action of Track 3.
- Backfill of historical missions is OUT OF SCOPE (NG-2, C-002). Do not add any code or script that iterates existing missions.

**Dependencies**: none
**Estimated prompt size**: ~320 lines
**Prompt file**: [tasks/WP04-mission-identity-phase-1.md](tasks/WP04-mission-identity-phase-1.md)

---

## WP05 — Track 5: Auth Refresh Race Fix

**Goal**: Extend the `filelock.FileLock` in `sync/auth.py` from per-I/O scope to the full `refresh_tokens()` transaction. On 401, re-read on-disk credentials under the same lock before treating the failure as terminal. This is a release-gating fix (FR-405) because background sync remains enabled in 3.1.1.

**Priority**: RELEASE GATE — 3.1.1 MUST NOT ship without this fix (FR-405).

**Spec FRs**: FR-401, FR-402, FR-403, FR-404, FR-405

**Subtasks**:
- [ ] T020 Extend `FileLock` scope in `refresh_tokens()` (WP05)
- [ ] T021 Re-read-on-401 path: stale 401 exits cleanly; real 401 clears under lock (WP05)
- [ ] T022 Verify httpx timeout < 10s lock timeout; set explicit timeout if needed (WP05)
- [ ] T023 Regression tests for Track 5 (WP05)

**Key technical notes**:
- The fix pattern: `with self._acquire_lock(): read; POST /token/refresh/; if 401: re-read, compare, decide; else: save`.
- `filelock.FileLock` is reentrant per-thread. Inner `load()`/`save()` calls inside the locked transaction reacquire the lock as no-ops — verify this assumption in test T5.4.
- The `saas_client.py:226-249` implementation already shows the correct refresh+retry-within-session pattern — use it as a reference.
- Background sync in `sync/background.py` uses a `threading.Lock` to serialize its own ticks. That lock is orthogonal to the cross-process `FileLock`. Do NOT change the `threading.Lock`.
- If the httpx client in `refresh_tokens()` does not have an explicit timeout configured, set one to 8s (< 10s lock timeout) to prevent a hung network request from deadlocking other CLI invocations.

**Dependencies**: none
**Estimated prompt size**: ~300 lines
**Prompt file**: [tasks/WP05-auth-refresh-race-fix.md](tasks/WP05-auth-refresh-race-fix.md)

---

## WP06 — Track 6: Implement De-emphasis

**Goal**: Remove top-level `spec-kitty implement` from all user-facing teach-out surfaces (README, slash-command source templates, docs canonical-path mentions). `spec-kitty implement` itself continues to run for compatibility and is now internal infrastructure. The canonical user workflow is `spec-kitty next` (loop) + `spec-kitty agent action implement/review` (per-decision verbs).

**Note**: The `init.py:641-650` next-steps edit is already in WP01 T003. WP06 handles all OTHER surfaces.

**Priority**: P1 — closes the remaining canonical-path teach-out gap.

**Spec FRs**: FR-501, FR-502, FR-503 (via WP03 T014), FR-504, FR-505, FR-506

**Subtasks**:
- [ ] T024 Update `README.md` canonical workflow + mermaid diagram (WP06)
- [ ] T025 Update slash-command source templates (WP06)
- [ ] T026 Update `docs/` canonical-path mentions (WP06)
- [ ] T027 Regression tests for Track 6 (WP06)

**Key technical notes**:
- `implement.py` docstring (FR-503) is covered by WP03 T014. WP06 does NOT touch `implement.py`.
- `README.md` lines 8-9: replace `` `spec` -> `plan` -> `tasks` -> `implement` -> `review` -> `merge` `` with language naming `spec-kitty next` as the loop step.
- Slash-command source templates `src/specify_cli/missions/software-dev/command-templates/`: replace any remaining `spec-kitty implement WP##` examples with `spec-kitty agent action implement <WP> --agent <name>`. The `/spec-kitty.implement` slash-command file itself stays but its body MUST resolve to `agent action implement`, not raw `spec-kitty implement`.
- Docs scope: update ONLY canonical-path mentions in the first ~5 paragraphs of ~12 files. Leave troubleshooting / recovery / how-to-deeply contexts alone.
- T027 tests should check: implement --help has "internal infrastructure" (already in WP03), README does not name `spec-kitty implement` in canonical path, templates teach `spec-kitty agent action implement`.

**Dependencies**: WP01 must be merged first (init.py next-steps already done there). WP03 must be merged first (`implement.py` docstring already done there). For the test assertions about init output and implement help, depend on WP01+WP03.

Actually — since WP06 does NOT own init.py or implement.py, and WP01 already covers the init next-steps and WP03 covers implement.py, WP06 can technically run in parallel with WP01 and WP03. Its owned files (README.md, templates, docs) are independent. The test assertions for T027 should be designed to test the final state after all WPs land; they don't need to run against an intermediate state.

**Dependencies**: none — owned files (README.md, templates, docs) are independent of all other WPs.
**Estimated prompt size**: ~300 lines
**Prompt file**: [tasks/WP06-implement-de-emphasis.md](tasks/WP06-implement-de-emphasis.md)

---

## WP07 — Track 7: Version Coherence and Release Gate Verification

**Goal**: Align `pyproject.toml` and `.kittify/metadata.yaml` versions; add the cross-file sync check to `validate_release.py`; verify the CHANGELOG-presence and structured-draft gates; run the dogfood acceptance walkthrough to confirm all 8 release gates (RG-1..RG-8) pass.

**Priority**: FINAL GATE — depends on all prior WPs being merged. This WP is the last step before tagging `v3.1.1`.

**Spec FRs**: FR-601, FR-602, FR-603, FR-604, FR-605, FR-606

**Subtasks**:
- [x] T028 Bump `.kittify/metadata.yaml` version (WP07)
- [x] T029 Add `validate_metadata_yaml_version_sync()` to `validate_release.py` (WP07)
- [x] T030 Verify CHANGELOG-presence check runs in branch mode; verify structured draft (WP07)
- [x] T031 Regression tests for Track 7 (WP07)
- [x] T032 Dogfood acceptance: run quickstart V-7; verify RG-1..RG-8 (WP07)

**Key technical notes**:
- Current state: `pyproject.toml:3` = `"3.1.1a3"`, `.kittify/metadata.yaml:6` = `"3.1.1a2"` — mismatch. T028 bumps metadata.yaml to `3.1.1a3`. The actual bump to `3.1.1` (stripping the alpha suffix) is a human action at release-cut time, gated by all RGs passing.
- `validate_release.py` already validates pyproject.toml + CHANGELOG. The new function adds the `.kittify/metadata.yaml` sync check and wires it into `main()` for branch mode.
- CHANGELOG-presence check: the existing `changelog_has_entry()` function already implements this. Verify it is called for the target version in branch mode; if not, add the call.
- Structured draft: `build_release_prep_payload(channel="stable", repo_root=...)` in `src/specify_cli/release/payload.py`. Verify it produces a payload with a non-empty `proposed_changelog_block` that starts with `## [3.1.1` or the current alpha version.
- T032 is the human-in-the-loop verification step. Run the quickstart.md §7 + §8 steps against `/private/tmp/311/spec-kitty`. Document the output as a comment in this WP file's history or as a commit message.

**Dependencies**: Depends on WP01, WP02, WP03, WP04, WP05, WP06 all being merged into `main` first.
**Estimated prompt size**: ~340 lines
**Prompt file**: [tasks/WP07-version-coherence.md](tasks/WP07-version-coherence.md)

---

## Parallelization Map

```
main
│
├── WP01 (Track 1: init)        ─────────────────────┐
├── WP02 (Track 4: parser)      ─────────────────────┤
├── WP03 (Track 2: planning)    ─────────────────────┤ all merge to main
├── WP04 (Track 3: identity)    ─────────────────────┤
├── WP05 (Track 5: auth)        ─────────────────────┤
├── WP06 (Track 6: de-emphasis) ─────────────────────┘
│                                         │
│                               WP07 (Track 7: version coherence + dogfood acceptance)
│                                         │
└──────────────────────────────── v3.1.1 tag (human action)
```

WP01–WP06: **fully parallel**, no file-ownership conflicts.
WP07: **sequential final gate**, runs after all prior WPs are merged.

---

## MVP Scope

**If limited to one WP**: WP01 (init coherence) — the most visible new-user regression and the most complained-about surface post-#555.

**Minimum releasable set**: WP01 + WP05 (init coherence + auth race fix, the two user-visible issues). WP02 (parser) is a close third since it protects new missions from silent parallelism collapse.

**For full release-readiness**: all 7 WPs must complete before WP07 can run its verification.

---

## Requirements Coverage

| WP | Spec FRs |
|----|---------|
| WP01 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008 |
| WP02 | FR-301, FR-302, FR-303, FR-304, FR-305 |
| WP03 | FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-503 (via T014) |
| WP04 | FR-201, FR-202, FR-203, FR-204, FR-205, FR-206 |
| WP05 | FR-401, FR-402, FR-403, FR-404, FR-405 |
| WP06 | FR-501, FR-502, FR-504, FR-505, FR-506 |
| WP07 | FR-601, FR-602, FR-603, FR-604, FR-605, FR-606 |
