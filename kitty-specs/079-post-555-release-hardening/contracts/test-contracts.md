# Test Contracts: 3.1.1 Post-555 Release Hardening

**Mission**: `079-post-555-release-hardening`
**Purpose**: Regression test scenarios that the implementation MUST satisfy. Each test contract maps to one or more FRs and is the acceptance gate for its track.

This document is the contract layer. The actual test code lives in `tests/` (per the file paths in `plan.md` §4 and §8). Reviewers and the `/spec-kitty.review` command use this document as the canonical "did the implementation satisfy the spec?" gate.

---

## Conventions

- **Test IDs** are `T<track>.<n>` where `<track>` is 1-7 and `<n>` is the test ordinal within that track.
- All tests MUST run under `PWHEADLESS=1 pytest tests/` and complete within the NFR-004 budget (< 60 s aggregate for new tests added by this mission).
- All tests MUST be deterministic. Concurrent / race tests use explicit synchronization primitives; no `time.sleep` based races.
- All file system tests MUST use `tmp_path` fixtures from pytest; they MUST NOT touch the working repo or the user's home directory.

---

## Track 1 — `init` coherence

### T1.1 — `init` does not create `.git/`

**File**: `tests/init/test_init_minimal_integration.py` (extension)
**Maps to**: FR-001
**Setup**: An empty `tmp_path`.
**Action**: Run `spec-kitty init demo --ai codex --non-interactive` against `tmp_path`.
**Assertions**:
- `(tmp_path / "demo" / ".git").exists() == False`
- `(tmp_path / ".git").exists() == False` (in case the target was tmp_path itself)

### T1.2 — `init` does not produce a commit

**File**: `tests/init/test_init_minimal_integration.py` (extension)
**Maps to**: FR-002
**Setup**: An empty `tmp_path`.
**Action**: Run `spec-kitty init demo --ai codex --non-interactive`.
**Assertions**:
- `subprocess.run(["git", "log"], cwd=tmp_path/"demo", capture_output=True).returncode != 0` (no git repo) OR
- The literal string `"Initial commit from Specify template"` does NOT appear anywhere under `tmp_path/"demo"` (grep across the directory).

### T1.3 — `init` does not create `.agents/skills/`

**File**: `tests/init/test_init_minimal_integration.py` (extension)
**Maps to**: FR-003
**Action**: Run `spec-kitty init demo --ai codex --non-interactive`.
**Assertions**:
- `(tmp_path / "demo" / ".agents" / "skills").exists() == False`

### T1.4 — `init` next-steps does not name top-level `spec-kitty implement`

**File**: `tests/init/test_init_next_steps.py` (NEW)
**Maps to**: FR-004, FR-501
**Action**: Capture stdout from `spec-kitty init demo --ai codex --non-interactive`.
**Assertions**:
- The captured stdout does NOT contain a line that names `spec-kitty implement` (the top-level CLI invocation) as a canonical implementation step.
- The captured stdout DOES name `spec-kitty next` as the canonical loop entry and `spec-kitty agent action implement` / `spec-kitty agent action review` as the per-decision verbs.
- Slash-command file names like `/spec-kitty.implement` MAY appear in the output (they refer to slash commands surfaced in the agent runtime, not top-level CLI invocations). What is FORBIDDEN is the literal string `spec-kitty implement WP` or any prose teaching top-level `spec-kitty implement` as a canonical user-facing CLI invocation.
- The captured stdout DOES NOT contain `Initial commit from Specify template`.

### T1.5 — `init` is idempotent on re-run

**File**: `tests/init/test_init_idempotent.py` (NEW)
**Maps to**: FR-006
**Setup**: A `tmp_path` that has already been initialized once.
**Action**: Run `spec-kitty init demo --ai codex --non-interactive` a second time.
**Assertions**: One of:
- Exit code 0, file set unchanged, message "already initialized" or equivalent. OR
- Exit code != 0, error message names the conflict.

### T1.6 — `init` does not touch existing git state

**File**: `tests/init/test_init_in_existing_repo.py` (NEW)
**Maps to**: FR-007
**Setup**: A `tmp_path` initialized as a git repo with one user-authored commit.
**Action**: Run `spec-kitty init demo --ai codex --non-interactive` against the same path.
**Assertions**:
- The git HEAD commit hash is unchanged before vs. after.
- The git branch is unchanged.
- `git status --porcelain` shows only the new files created by init (no modified existing files).
- No new commits exist in the git log.

### T1.7 — `init --help` describes the new model

**File**: `tests/init/test_init_help.py` (NEW or extend)
**Maps to**: FR-008
**Action**: Capture stdout from `spec-kitty init --help`.
**Assertions**:
- Help text mentions "no automatic git initialization" (or equivalent phrasing).
- Help text mentions "no automatic commit" (or equivalent).
- Help text names `spec-kitty next` and `spec-kitty agent action implement/review` as the canonical user-facing path.
- Help text confirms the `--no-git` flag is no longer present (P1: removed in 3.1.1).

---

## Track 2 — Planning-artifact producer correctness

### T2.1 — `compute_lanes` includes planning-artifact WPs

**File**: `tests/lanes/test_compute_planning_artifact.py` (NEW)
**Maps to**: FR-101
**Setup**: A test fixture mission with one code WP and one planning-artifact WP. Build the dependency graph and ownership manifests.
**Action**: Call `compute_lanes(dependency_graph, ownership_manifests, mission_slug, target_branch, ...)`.
**Assertions**:
- The returned `LanesManifest.lanes` list contains a lane whose `lane_id == "lane-planning"`.
- That lane's `wp_ids` includes the planning-artifact WP.

### T2.2 — Planning lane has canonical id

**File**: `tests/lanes/test_compute_planning_artifact.py` (NEW)
**Maps to**: FR-102
**Action**: Same as T2.1.
**Assertions**:
- The lane id is exactly `"lane-planning"` (canonical, not derived from the mission slug).

### T2.3 — `lane_branch_name` for `lane-planning` returns the planning branch

**File**: `tests/lanes/test_branch_naming_planning.py` (NEW)
**Maps to**: FR-103
**Action**: Call `lane_branch_name("079-post-555-release-hardening", "lane-planning")`.
**Assertions**:
- The returned string equals the mission's `target_branch` value (e.g., `"main"`), NOT `"kitty/mission-079-post-555-release-hardening-lane-planning"`.

### T2.4 — Resolver returns coherent ref for planning-artifact WP via lane lookup

**File**: `tests/context/test_resolver_planning_artifact.py` (NEW)
**Maps to**: FR-104, FR-105
**Setup**: A mission with at least one planning-artifact WP, lanes computed.
**Action**: Call `context.resolver.resolve_authoritative_ref(feature_dir, mission_slug, planning_wp_id)`.
**Assertions**:
- The returned ref is the planning branch (e.g., `"main"`).
- The function does NOT raise `MissingIdentityError`.
- The function does NOT branch on `execution_mode == "planning_artifact"` at the lane lookup site (verifiable via code review or by injecting a mock that asserts the call path).

### T2.5 — `implement` dispatch resolves planning-artifact WP to main repo checkout

**File**: `tests/agent/cli/commands/test_implement_planning_artifact.py` (NEW)
**Maps to**: FR-105
**Setup**: A mission with at least one planning-artifact WP, lanes computed.
**Action**: Invoke `spec-kitty implement <planning_wp_id> --mission <slug>`.
**Assertions**:
- The resolved workspace path is `paths.get_main_repo_root(working_dir)`, NOT `.worktrees/<slug>-lane-planning`.
- No `.worktrees/<slug>-lane-planning` directory was created.
- Exit code 0.

### T2.6 — Code WPs continue to receive normal lane assignments

**File**: `tests/lanes/test_compute_planning_artifact.py` (NEW)
**Maps to**: FR-106 (regression coverage for the unchanged path)
**Setup**: Same as T2.1.
**Action**: Same as T2.1.
**Assertions**:
- The code WP receives a `lane-a`/`lane-b` style lane id (NOT `lane-planning`).
- The code WP's lane has a non-empty `write_scope`.

---

## Track 3 — Mission identity Phase 1

### T3.1 — `mission_id` is minted at creation

**File**: `tests/core/test_mission_creation_identity.py` (NEW)
**Maps to**: FR-201
**Action**: Call `core.mission_creation.create_mission_core(repo_root, "test-identity")` against a `tmp_path` repo.
**Assertions**:
- Read `<feature_dir>/meta.json`.
- `meta["mission_id"]` exists, is a string, is non-empty.
- The string parses as a valid ULID via `ulid.ULID.from_str(meta["mission_id"])`.

### T3.2 — `mission_id` does not depend on numeric prefix scan

**File**: `tests/core/test_mission_creation_identity.py` (NEW)
**Maps to**: FR-204
**Setup**: A `tmp_path` repo with two existing missions at `kitty-specs/001-foo/` and `kitty-specs/099-bar/`.
**Action**: Call `core.mission_creation.create_mission_core(tmp_path, "new-mission")`.
**Assertions**:
- The new mission's `mission_id` is a valid ULID.
- The `mission_id` value does NOT depend on the numeric prefix value (i.e., creating the same mission name in a different repo with different prefixes yields a different `mission_id`).
- The numeric prefix is `"100"` (display-friendly, max+1) — this confirms `get_next_feature_number()` still works for display, but the `mission_id` is independently generated.

### T3.3 — Concurrent mission creation does not collide

**File**: `tests/core/test_mission_creation_concurrent.py` (NEW)
**Maps to**: FR-205
**Setup**: Two independent `tmp_path` repos OR two threads operating on the same repo with different slugs.
**Action**: Spawn two threads that each call `create_mission_core` with distinct slugs.
**Assertions**:
- Both `meta.json` files exist.
- Both have `mission_id` values.
- The two `mission_id` values are different.
- Both threads exit cleanly (no exceptions, no truncated writes).

### T3.4 — `MissionIdentity` exposes `mission_id`

**File**: `tests/mission_metadata/test_mission_identity_includes_id.py` (NEW or extend existing)
**Maps to**: FR-202
**Setup**: A mission `meta.json` with `mission_id`.
**Action**: Call `mission_metadata.resolve_mission_identity(feature_dir)`.
**Assertions**:
- The returned `MissionIdentity` has a `mission_id` attribute.
- The attribute equals the value from `meta.json`.

### T3.5 — `MissionIdentity` tolerates legacy missions without `mission_id`

**File**: `tests/mission_metadata/test_mission_identity_legacy.py` (NEW or extend)
**Maps to**: NG-2 (legacy tolerance for display only)
**Setup**: A mission `meta.json` WITHOUT `mission_id` (simulating a historical mission).
**Action**: Call `mission_metadata.resolve_mission_identity(feature_dir)`.
**Assertions**:
- The returned `MissionIdentity` has `mission_id is None`.
- Other fields (`mission_slug`, `mission_number`, `mission_type`) are populated normally.

### T3.6 — `emit_mission_created` payload includes `mission_id`

**File**: `tests/sync/test_emit_mission_created_includes_mission_id.py` (NEW)
**Maps to**: FR-202 (machine-facing flows identify by `mission_id`)
**Action**: Call `sync.events.emit_mission_created(mission_slug=..., mission_number=..., mission_id=..., ...)`.
**Assertions**:
- The emitted payload (JSON) contains `mission_id` as a top-level field.
- The value matches the input.

---

## Track 4 — Tasks/finalize hotfix

### T4.1 — Final WP section bounds at top-level non-WP heading

**File**: `tests/core/test_dependency_parser.py` (extension)
**Maps to**: FR-301
**Setup**:
```markdown
## WP01

**Dependencies**: WP00

Body of WP01.

## WP02

**Dependencies**: []

Body of WP02.

## Notes

This phase depends on WP01 being complete and signed off. Depends on WP01.
```
**Action**: Call `parse_dependencies_from_tasks_md(content)`.
**Assertions**:
- `result == {"WP01": ["WP00"], "WP02": []}`
- Specifically: `"WP02": []` — the trailing prose under `## Notes` is NOT parsed into WP02's dependencies.

### T4.2 — Trailing prose without a `## ` heading still bounds at EOF

**File**: `tests/core/test_dependency_parser.py` (extension)
**Maps to**: FR-301 (edge case)
**Setup**:
```markdown
## WP01

**Dependencies**: []

Body of WP01.

This is an unstructured trailing paragraph that mentions WP02 informally.
```
**Action**: Call `parse_dependencies_from_tasks_md(content)`.
**Expected behavior**: The current behavior is that trailing prose after the final WP without a `## ` heading **is** parsed (this is the underlying #525 issue). For Track 4's narrow slice, the chosen design is to bound at `## ` headings only — trailing free-form prose remains a known issue documented in `research.md` rejected alternatives. **This test is a NEGATIVE assertion**: it documents the known limitation and asserts the parser correctly identifies WP02 in this edge case OR returns `[]` if the parser otherwise improves. The test name should make this clear.
**Assertion**: The test passes if `result["WP01"]` is either `[]` or `["WP02"]`. The point is to have the test exist as a tripwire — if a future change tightens the bound, this test catches the regression in the **other** direction.

(Reviewer note: T4.2 is a deliberate documentation test for the known #525 boundary; the strict bound is FR-301, which T4.1 covers. Discuss with the reviewer if T4.2 should be removed for clarity — keeping it preserves the test as a sentinel for the next iteration.)

### T4.3 — Sub-headings inside a WP section do NOT trigger the bound

**File**: `tests/core/test_dependency_parser.py` (extension)
**Maps to**: FR-301 (edge case)
**Setup**:
```markdown
## WP01

**Dependencies**: WP00

### Implementation notes

Some implementation notes here.

### Test plan

- Depends on WP02

## WP02

Body.
```
**Action**: Call `parse_dependencies_from_tasks_md(content)`.
**Assertions**:
- `result["WP01"]` includes both `WP00` AND `WP02` (the bullet-list under `### Test plan` is inside WP01's section because `###` does not trigger the bound).
- This validates that sub-headings within a WP section are preserved.

### T4.4 — Explicit `dependencies:` declaration is preserved verbatim

**File**: `tests/core/test_dependency_parser.py` (extension)
**Maps to**: FR-302, FR-303
**Setup**: A `tasks.md` where WP02 has explicit `dependencies: []` in frontmatter and no inline `Depends on` text.
**Action**: Run finalize-tasks against the file.
**Assertions**:
- The finalized manifest's WP02 has `dependencies: []`.
- The disagree-loud check did not fire (no error).

---

## Track 5 — Auth refresh race fix

### T5.1 — `refresh_tokens` holds the lock for the full transaction

**File**: `tests/sync/test_auth_concurrent_refresh.py` (NEW)
**Maps to**: FR-401
**Action**: Patch the HTTP client to introduce an artificial delay; in a second thread, attempt to acquire the same `FileLock` and assert it blocks until the refresh completes.
**Assertions**:
- The second thread's lock acquisition blocks for at least the duration of the network delay.
- After the refresh completes, the second thread acquires the lock and proceeds.

### T5.2 — Stale 401 does not clear credentials

**File**: `tests/sync/test_auth_concurrent_refresh.py` (NEW)
**Maps to**: FR-402, FR-403
**Setup**: Two threads. Thread A starts a refresh (mocked HTTP returns 200 with new tokens). Thread B starts a refresh (mocked HTTP returns 401) where, between B's lock release at function entry and B's network call return, A has already rotated the token on disk.
**Action**: Both threads run.
**Assertions**:
- Thread A: completes successfully, on-disk token is the new rotated value.
- Thread B: detects the on-disk token has changed since function entry, exits cleanly without clearing.
- After both threads complete, the credentials file still exists and contains Thread A's rotated tokens.

### T5.3 — Real (non-stale) 401 still clears credentials

**File**: `tests/sync/test_auth_concurrent_refresh.py` (NEW)
**Maps to**: FR-403
**Setup**: A single thread. Mocked HTTP returns 401. No concurrent rotation occurs.
**Action**: Call `refresh_tokens()`.
**Assertions**:
- The function reads on-disk credentials, finds them unchanged from function entry, treats the 401 as authoritative, clears credentials.
- Raises `AuthenticationError`.
- The credentials file no longer exists.

### T5.4 — Reentrancy: inner `load`/`save` calls are no-op lock acquisitions

**File**: `tests/sync/test_auth_concurrent_refresh.py` (NEW)
**Maps to**: FR-401
**Action**: Mock the lock to count acquisitions; call `refresh_tokens()`.
**Assertions**:
- The lock is acquired exactly once at function entry by the same thread.
- Inner `load()` / `save()` calls do NOT cause additional cross-process lock acquisitions (they reacquire the in-memory thread-local lock state without blocking).

---

## Track 6 — Top-level `implement` de-emphasis

### T6.1 — `spec-kitty implement --help` marks compatibility surface

**File**: `tests/agent/cli/commands/test_implement_help.py` (NEW)
**Maps to**: FR-503
**Action**: Capture stdout from `spec-kitty implement --help`.
**Assertions**:
- The text contains the phrase `"internal infrastructure"` or `"implementation detail"` (marking the command as not part of the canonical user-facing path).
- The text contains a literal reference to `spec-kitty next` (the canonical loop) AND a literal reference to `spec-kitty agent action implement` (the canonical per-WP verb).
- The text MAY also describe the command as a "compatibility surface" for direct invokers, but the primary framing MUST be "internal infrastructure".

### T6.2 — `spec-kitty implement` still runs

**File**: `tests/agent/cli/commands/test_implement_runs.py` (extend existing or NEW)
**Maps to**: FR-505
**Setup**: A mission with finalized lanes containing at least one code WP.
**Action**: Invoke `spec-kitty implement WP01 --mission <slug>`.
**Assertions**:
- Exit code 0.
- The lane worktree was allocated or reused.
- The command produced its expected output (JSON or human, per mode).

### T6.3 — `init` next-steps does not name top-level `spec-kitty implement`

(Same as T1.4 — overlap with Track 1.)

### T6.4 — `README.md` does not name top-level `spec-kitty implement` in canonical workflow

**File**: `tests/docs/test_readme_canonical_path.py` (NEW)
**Maps to**: FR-502
**Setup**: Read `README.md` from the working repo.
**Assertions**:
- The string `\`implement\`` does NOT appear in the canonical workflow line at lines ~8-9 (or wherever the canonical workflow line ends up after the rewrite).
- The mermaid / ASCII diagram (lines ~64-80) does NOT name `spec-kitty implement` as a step.
- A more semantic check: the README's "getting started" section refers users to `spec-kitty next` (the loop) and `spec-kitty agent action implement` / `spec-kitty agent action review` (the per-decision verbs), not to top-level `spec-kitty implement`.

### T6.5 — Slash-command source templates do not teach top-level `spec-kitty implement`

**File**: `tests/missions/test_command_templates_canonical_path.py` (NEW)
**Maps to**: FR-504
**Setup**: Read each file under `src/specify_cli/missions/software-dev/command-templates/`.
**Assertions**:
- The literal string `spec-kitty implement WP` (top-level CLI invocation form) does NOT appear in `tasks.md`, `tasks-packages.md`, `specify.md`, `plan.md`, or `implement.md` as a canonical user-facing example.
- Where the templates need to reference the implement step, they use `spec-kitty agent action implement <WP> --agent <name>` (the agent-facing wrapper that handles workspace creation internally) and/or `spec-kitty next --agent <name> --mission <slug>` (the loop entry).
- The slash-command file `/spec-kitty.implement` MAY remain as a slash command, but its body MUST resolve to `spec-kitty agent action implement` invocation, not to the top-level `spec-kitty implement` invocation.

---

## Track 7 — Repo dogfood / version coherence

### T7.1 — `validate_release.py` fails on metadata-yaml ↔ pyproject mismatch

**File**: `tests/release/test_validate_metadata_yaml_sync.py` (NEW)
**Maps to**: FR-601, FR-602
**Setup**: A `tmp_path` repo with `pyproject.toml` (`version = "3.1.1"`) and `.kittify/metadata.yaml` (`spec_kitty.version: 3.1.1a3`).
**Action**: Run `python scripts/release/validate_release.py` against the temp repo.
**Assertions**:
- Exit code != 0.
- stderr or stdout contains both file paths and both version values in the error message.

### T7.2 — `validate_release.py` passes when versions match

**File**: `tests/release/test_validate_metadata_yaml_sync.py` (NEW)
**Maps to**: FR-601
**Setup**: A `tmp_path` repo with both files reporting `3.1.1`, plus a `CHANGELOG.md` that has a `## [3.1.1]` entry.
**Action**: Run `python scripts/release/validate_release.py`.
**Assertions**:
- Exit code 0.

### T7.3 — `validate_release.py` fails when CHANGELOG entry is missing

**File**: `tests/release/test_validate_changelog_entry.py` (NEW or extend existing)
**Maps to**: FR-606
**Setup**: A `tmp_path` repo with matching versions but a `CHANGELOG.md` that has NO `## [3.1.1]` entry.
**Action**: Run `python scripts/release/validate_release.py` in branch mode.
**Assertions**:
- Exit code != 0.
- The error message names the missing entry.

### T7.4 — `build_release_prep_payload` produces a valid draft

**File**: `tests/release/test_release_payload_draft.py` (NEW)
**Maps to**: FR-605
**Setup**: A `tmp_path` repo with at least one accepted WP under `kitty-specs/<some-mission>/tasks/done/`.
**Action**: Call `build_release_prep_payload(channel="stable", repo_root=tmp_path)`.
**Assertions**:
- The returned payload is a dict.
- The payload has a `proposed_changelog_block` key.
- The value of `proposed_changelog_block` is a non-empty string.
- The string contains a header that references a stable version (e.g., starts with `## [3.1.1`).

### T7.5 — Dogfood command set runs cleanly

**File**: `tests/release/test_dogfood_command_set.py` (NEW)
**Maps to**: FR-603, FR-604
**Setup**: Use the working repo path (`/private/tmp/311/spec-kitty`) at the release commit. The test is gated on `os.environ.get("SPEC_KITTY_DOGFOOD_TEST") == "1"` so it runs only in CI / explicit dogfood mode (it touches the real filesystem).
**Action**: Invoke each command from the dogfood set:
1. `spec-kitty --version`
2. `spec-kitty init demo --ai codex --non-interactive` (in a `tmp_path`)
3. `spec-kitty agent mission create dogfood-test --json` (in `/private/tmp/311/spec-kitty`)
4. `spec-kitty agent mission finalize-tasks --mission dogfood-test`
5. `spec-kitty agent tasks status --mission dogfood-test`

**Assertions**:
- Each command exits 0.
- No command output contains the substring `version` followed by a mismatched version string.
- After the test completes, the `dogfood-test` mission is cleaned up from `/private/tmp/311/spec-kitty/kitty-specs/`.

---

## Cross-track integration tests

### TX.1 — `quickstart.md` walkthrough completes

**File**: `tests/integration/test_quickstart_walkthrough.py` (NEW)
**Maps to**: All tracks
**Setup**: Same gating as T7.5 (SPEC_KITTY_DOGFOOD_TEST=1).
**Action**: Execute every step in `quickstart.md` against `/private/tmp/311/spec-kitty` at the release commit.
**Assertions**:
- Every step exits as expected (most exit 0; the deliberate-failure steps exit non-zero with the expected error message).
- The walkthrough completes within 5 minutes.

---

## Aggregate runtime budget

| Test category | Estimated runtime |
|---------------|-------------------|
| Track 1 (5 tests) | < 5 s |
| Track 2 (6 tests) | < 8 s |
| Track 3 (6 tests) | < 6 s |
| Track 4 (4 tests) | < 2 s |
| Track 5 (4 tests) | < 10 s (concurrent threading + lock waits) |
| Track 6 (5 tests) | < 5 s |
| Track 7 (4 tests, T7.5 gated) | < 5 s (T7.5 + TX.1 are gated) |
| **Total (un-gated, in pre-commit gate)** | **< 41 s** — within NFR-004 budget (< 60 s) |
| TX.1 + T7.5 (CI / dogfood mode only) | < 5 minutes |

---

## Out-of-scope assertions (PR-review only, no test code)

| FR | Assertion | Enforced by |
|----|-----------|-------------|
| FR-206 | No backfill of historical missions' identity | PR review |
| FR-305 | No full manifest redesign for #525 | PR review |
| FR-506 | No partial fix for #538/#540/#542 | PR review |
| NG-1 | No `kitty-specs/**` archaeology | PR review + scope-audit (RG-8) |
| NG-6 | No SaaS contract surface area added | PR review |
| C-012 | No final CHANGELOG.md prose authored by mission | PR review |
