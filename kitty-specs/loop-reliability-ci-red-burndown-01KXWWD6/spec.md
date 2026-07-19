# Mission Specification: Loop-reliability + CI-red burndown remediation

**Mission Branch**: `fix/loop-reliability-ci-red-burndown`
**Created**: 2026-07-19
**Status**: Draft
**Input**: A narrow remediation slice (scoped by a planner-priti feasibility pass) that lands the
*ready* fixes for two implement-review-loop P0s and burns down the tracked 3.2.x CI reds, behind a
shared per-test sync-env-reset enabler. Two lanes: ready product-bug fixes + CI-red hygiene.

## Context & Grounding *(planner-priti feasibility pass; re-verify if extending)*

- **#2534** (P0, consumer-repo pre-review gate) — a **ready** fix exists on a **local-only** branch
  `fix/2534-pre-review-gate-consumer-repo` (tip `0153934f9`, +142/−3 across 4 files, red-first tests
  included). It adds an `is_consumer_repo` seam so the gate **calm-degrades** to a non-blocking
  `no_coverage` warn instead of the alarming "gate authorities unavailable" message. The branch is
  **309 commits behind main** and touches `pre_review_gate.py` + `tasks_move_task.py` (both churned
  since) — **the rebase is the risk, not the fix.** The coupling still lives on main
  (`pre_review_gate.py:104,106,156` import `tests.architectural._gate_coverage`). The by-construction
  fix (#2598) is **epic-blocked** under #2535/#2466 (no PR; depends on #2535 step-3) → land the branch
  now; #2598 supersedes later.
- **#2573b** (P0, sub-scope of #2573) — the sync daemon is deaf to `SPEC_KITTY_SYNC_DISABLE` /
  `SPEC_KITTY_SYNC_MINIMAL_IMPORT`. Red-first repro `tests/sync/test_daemon_sync_disable_env.py`
  exists and is red. The `--skip-pre-review-gate` flag half already landed (fast-follow). Only the
  daemon-env-honoring half remains here; the **non-blocking/streamed-gate design axis (#2573a-deep)
  is explicitly out of scope.**
- **CI-red hygiene** (non-P0, 3.2.x-milestoned): **#2807** (4 charter synthesize/evidence/bundle
  reds), **#2809** (`test_strict_json_stdout` strict-JSON-under-sync-skip), **#2812** (urn-lane
  warnings-registry flake + mission-loader-coverage skip anomaly).
- **Cross-lane synergy:** #2573b (daemon honors the disable env) and #2809 (isolate the strict-JSON
  test from the globally-leaked sync toggle) are two sides of the same sync-env-toggle seam — a shared
  per-test env-reset fixture (**WP-A**, mirroring #2800's pre-review-gate isolation) enables both.

### Explicitly out of scope (deferred by design — do NOT fold)
- **#2795 / #2367-A** (merge coord-worktree tool-churn) — deliberately split out, deferred, reuses the
  #2222 churn classifier; its own design mission.
- **#2573a-deep** — non-blocking/streamed gate; #2573 stays open for it after (b) lands.
- **#2598** — epic-blocked under #2535; stays tracked there.

### Related (referenced, not folded whole) — post-plan squad
- **#2555** point 2 (`ensure_sync_daemon` deaf to the disable env) is the *same fix* as #2573b (per #2573's
  body) — closed in-mission via FR-003; #2555's other points stay open under #2017/#2160.
- **#2782** tracks the *same test* as #2809 (`test_strict_json_stdout`) with a *divergent* root cause (sync
  connection-refused vs #2809's leaked toggle). FR-005's WP must red-first confirm the env-reset fixture
  actually greens the test on current main (LM-7); if the #2782 cause is live, #2782 stays open.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The pre-review gate stops blocking legitimate consumer-repo work (Priority: P1)

An operator running `move-task --to for_review` in a **consumer repo** (not spec-kitty's own) no
longer hits the alarming "gate authorities unavailable" failure — the gate calm-degrades to a
non-blocking `no_coverage` warn, so the transition proceeds.

**Why this priority**: P0 workflow reliability (#2534); the ready fix just needs landing.

**Independent Test**: On a fresh consumer-repo fixture, `move-task --to for_review` completes with a
`no_coverage` warn (not a hard failure); the branch's red-first repros go green after rebase.

**Acceptance Scenarios**:
1. **Given** a consumer repo without a spec-kitty-shaped `tests/architectural/_gate_coverage`, **When**
   `move-task --to for_review` runs, **Then** the gate emits a non-blocking `no_coverage` warn and the
   transition applies (no "gate authorities unavailable" hard failure).
2. **Given** spec-kitty's own repo, **When** the gate runs, **Then** behavior is unchanged (still
   verifies real scope).

---

### User Story 2 - The sync daemon honors the disable env (Priority: P1)

Setting `SPEC_KITTY_SYNC_DISABLE` (or `SPEC_KITTY_SYNC_MINIMAL_IMPORT`) actually prevents the sync
daemon from spawning, so gate/loop operations under that env don't hang on a daemon fan-out.

**Why this priority**: P0 (#2573b); the red-first repro is already written and failing.

**Independent Test**: `tests/sync/test_daemon_sync_disable_env.py` flips red→green — with the env set,
the daemon does not spawn (`outcome.started is False`).

**Acceptance Scenarios**:
1. **Given** `SPEC_KITTY_SYNC_DISABLE=1`, **When** an op that would spawn the sync daemon runs, **Then**
   the daemon is not spawned.
2. **Given** a falsy/unset env, **When** the same op runs, **Then** the daemon spawns as before
   (behavior-preserving).

---

### User Story 3 - The 3.2.x blocking/fast CI jobs are free of untracked reds (Priority: P2)

The `regression (blocking)` and `fast-tests-charter` jobs carry only genuinely-tracked reds — the
charter fixture/evidence reds, the strict-JSON test, and the urn-lane flake are fixed or
xfail-with-a-tracking-reference, so releasability isn't muddied by mystery reds.

**Why this priority**: P2 CI hygiene (#2807/#2809/#2812); enables a clean release gate.

**Independent Test**: the three named CI reds are each either green or an xfail carrying an explicit
issue reference; the blocking regression job has no untracked red.

**Acceptance Scenarios**:
1. **Given** the charter fixture remainder (`test_bundle_contract` charter.yaml-on-disk), **When** the
   test runs, **Then** it is fixed (green).
2. **Given** the long-standing `'str' object has no attribute 'get'` evidence-path red, **When** it
   cannot be fixed in-slice, **Then** it is `xfail(reason=..., strict)` with a tracking-issue ref.
3. **Given** the urn-lane warnings-registry flake, **When** the suite runs in parallel, **Then** the
   flake is root-fixed (registry reset), not retried.

---

### Edge Cases

- **fix/2534 rebase drift**: the branch is 309 commits behind and touches churned files — the repro
  must be confirmed to *still fire on current main* before assuming a clean cherry-pick (LM-1).
- **`'str'.get` evidence red**: a real synthesize bug of unknown depth — if not fixably small in-slice,
  xfail-with-ref rather than fabricate a fix (LM-3).
- **mission-loader-coverage skip anomaly**: CI-orchestration (filter-vs-`if:` guard) of unknown depth —
  if it balloons, split to its own issue rather than swelling this mission (LM-4).
- **Env-reset fixture leakage**: WP-A must reset `SPEC_KITTY_SYNC_*` per-test without mutating the real
  process env for sibling tests (the #2800 isolation pattern).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Shared per-test sync-env-reset fixture (enabler) | As a maintainer, I want a per-test fixture that resets `SPEC_KITTY_SYNC_DISABLE`/`MINIMAL_IMPORT` (mirroring #2800's isolation) so sync-env-sensitive tests are deterministic. | High | Open |
| FR-002 | Land the consumer-repo gate calm-degrade (#2534) | As an operator, I want `move-task --to for_review` in a consumer repo to calm-degrade to a non-blocking `no_coverage` warn — by rebasing and landing the ready `fix/2534` branch (`0153934f9`), re-verifying its red-first repros. | High | Open |
| FR-003 | Sync daemon honors the disable env (#2573b) | As an operator, I want `SPEC_KITTY_SYNC_DISABLE`/`MINIMAL_IMPORT` to prevent daemon spawn — flip `test_daemon_sync_disable_env.py` red→green. | High | Open |
| FR-004 | Adjudicate the 4 charter CI reds (#2807) | As a release manager, I want the charter fixture remainder fixed (`test_bundle_contract`) and the `'str'.get` evidence/synthesize red either fixed or xfail-with-tracking-ref. | Medium | Open |
| FR-005 | Isolate the strict-JSON test (#2809) | As a maintainer, I want `test_strict_json_stdout::test_mission_create_json_strict_when_sync_skips_ingress` isolated via the WP-A fixture (or xfail-with-ref) so it is deterministic in CI. | Medium | Open |
| FR-006 | Root-fix the urn-lane flake + triage the loader anomaly (#2812) | As a maintainer, I want the urn-lane warnings-registry flake root-fixed (registry reset per flakiness policy) and the mission-loader-coverage skip anomaly triaged (fixed or split-out). | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Blocking/fast jobs untracked-red-free | After the mission, the `regression (blocking)` and `fast-tests-charter` jobs carry zero untracked reds; every remaining red is fixed or an xfail carrying an explicit issue reference. | Reliability | High | Open |
| NFR-002 | No unjustified suppression | ruff + mypy --strict clean; no bare `xfail`/`skip`/`# type: ignore` — any xfail is `strict` and carries a tracking-issue reference; prefer a real fix over xfail. | Maintainability | High | Open |
| NFR-003 | Behavior-preserving product fixes | The #2534 and #2573b fixes change only the intended behavior (consumer-repo calm-degrade; daemon env-honoring); spec-kitty-repo gate behavior and daemon-on-unset behavior are unchanged. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Exclude deferred-by-design work | Do NOT fold #2795/#2367-A (deferred merge design), #2573a-deep (non-blocking/streamed gate design axis), or #2598 (epic-blocked under #2535). | Technical | High | Open |
| C-002 | #2534 is land-not-redesign | #2534 ships by rebasing + landing the existing `fix/2534` branch (`0153934f9`), not by re-deriving a fix; #2598 supersedes by-construction later under #2535. | Technical | High | Open |
| C-003 | ATDD red-first through existing repros | Flip the pre-existing red-first repros (`test_daemon_sync_disable_env`, the fix/2534 tests, the charter reds) red→green; do not author new entry points where one exists. | Technical | High | Open |
| C-004 | Parenting unchanged | Product P0s stay under their existing epics (#2573→#2017, #2534→#2535 via #2598); no new mega-epic. The CI-red issues are 3.2.x-milestoned. | Process | Medium | Open |
| C-005 | Split, don't swell | If the mission-loader-coverage anomaly (#2812) or the `'str'.get` evidence red (#2807) balloons beyond in-slice hygiene, split to its own issue rather than expanding this mission. | Technical | Medium | Open |

### Key Entities

- **`fix/2534` branch** (`0153934f9`): the ready consumer-repo calm-degrade fix to rebase + land.
- **`test_daemon_sync_disable_env.py`**: the #2573b red-first repro to flip green.
- **WP-A env-reset fixture**: the shared per-test `SPEC_KITTY_SYNC_*` isolation enabler (mirrors #2800).
- **CI-red set**: `test_bundle_contract` + the `'str'.get` evidence red (#2807), `test_strict_json_stdout`
  (#2809), the urn-lane flake + mission-loader anomaly (#2812).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `tests/sync/test_daemon_sync_disable_env.py` is green (daemon honors the disable env).
- **SC-002**: the `fix/2534` red-first repros are green on the rebased branch; a consumer-repo
  `move-task --to for_review` calm-degrades (no hard "gate authorities unavailable").
- **SC-003**: the `regression (blocking)` job has zero untracked reds; every remaining red is fixed or
  an `xfail(strict)` with an issue reference.
- **SC-004**: `test_strict_json_stdout` and `test_bundle_contract` are green (or xfail-with-ref); the
  urn-lane flake is root-fixed (0 flake across N parallel runs).
- **SC-005**: `ruff check .` + `mypy --strict` on touched files pass with zero new unjustified
  suppressions; issue-matrix resolves #2534, #2573, #2807, #2809, #2812.
