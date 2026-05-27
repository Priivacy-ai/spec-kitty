---
work_package_id: WP07
title: Shared-package events drift residual
dependencies: []
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
agent: claude
history:
- date: '2026-05-27'
  event: created
agent_profile: debugger-debbie
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/restart.py
- src/specify_cli/sync/**
- src/specify_cli/spec_kitty_events/
- tests/sync/**
- tests/contract/**
role: investigator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load debugger-debbie
```

---

## Objective

Fix six residual structural failures from the shared-package events alignment done in mission 01KSF9HJ. The version alignment was completed; these are structural issues that survived the version fix.

**Closes**: GitHub issue #1301

---

## Context

The `spec_kitty_events` package version is already pinned correctly in `uv.lock`. Do NOT change the package version. The six items are structural: a daemon-allowlist entry, two init-time event queuing gaps, a fixture payload schema mismatch, a vendored directory that should not exist, and a missing YAML frontmatter comment.

**Before starting**: confirm the installed package version matches the lock file:
```bash
uv sync --frozen
python -c "import spec_kitty_events; print(spec_kitty_events.__version__)"
```

---

## Subtask T026 — Add restart.py to daemon-allowlist (or refactor unauthorized call)

**Purpose**: `tests/sync/test_daemon_intent_gate.py` has an allowlist of files that are permitted to make daemon-intent calls. `src/specify_cli/sync/restart.py` is making such a call but is not in the allowlist.

**Steps**:

1. Run the test to understand the failure:
   ```bash
   pytest tests/sync/test_daemon_intent_gate.py -v --tb=long 2>&1 | head -60
   ```

2. Read the allowlist in the test and the call in `restart.py`:
   ```bash
   grep -n "allowlist\|allow_list\|allowed" tests/sync/test_daemon_intent_gate.py | head -10
   grep -n "daemon\|intent" src/specify_cli/sync/restart.py | head -10
   ```

3. Determine the correct fix:
   - If `restart.py` legitimately needs to make a daemon-intent call: add it to the allowlist in the test
   - If the call in `restart.py` is an error: refactor the function to remove the unauthorized call

4. Run the test to confirm:
   ```bash
   pytest tests/sync/test_daemon_intent_gate.py -v
   ```

**Validation**:
- [ ] `test_daemon_intent_gate` passes
- [ ] The decision (allowlist vs. refactor) is documented in the commit message

---

## Subtask T027 — Fix BuildRegistered not queued at init

**Purpose**: `BuildRegistered` should be queued when the sync subsystem initializes. It is currently not being queued.

**Steps**:

1. Run the lifecycle-readiness test:
   ```bash
   pytest tests/sync/ -v --tb=long -k "lifecycle_readiness or BuildRegistered" 2>&1 | head -60
   ```

2. Find the init path in `src/specify_cli/sync/`:
   ```bash
   grep -rn "BuildRegistered\|build_registered" src/specify_cli/sync/ | head -10
   ```

3. Add the event queue call at init time. Follow the existing pattern for other events queued at init.

4. Run the test to confirm:
   ```bash
   pytest tests/sync/ -v --tb=short -k "lifecycle_readiness"
   ```

**Files**: `src/specify_cli/sync/` (init path)

**Validation**:
- [ ] `BuildRegistered` is queued at init
- [ ] Related test passes

---

## Subtask T028 — Fix MissionOriginBound not queued without WebSocket

**Purpose**: When no WebSocket is available, `MissionOriginBound` should be queued to the offline queue. It is currently dropped.

**Steps**:

1. Run the relevant test:
   ```bash
   pytest tests/sync/ -v --tb=long -k "no_websocket or MissionOriginBound" 2>&1 | head -60
   ```

2. Locate the WebSocket availability check in `src/specify_cli/sync/`:
   ```bash
   grep -rn "MissionOriginBound\|offline_queue\|websocket" src/specify_cli/sync/ | head -15
   ```

3. Add the offline-queue enqueue call for `MissionOriginBound` in the no-WebSocket path.

4. Run the test to confirm:
   ```bash
   pytest tests/sync/ -v --tb=short -k "no_websocket or MissionOriginBound"
   ```

**Files**: `src/specify_cli/sync/` (offline queue path)

**Validation**:
- [ ] `MissionOriginBound` is queued when WebSocket is unavailable
- [ ] Related test passes

---

## Subtask T029 — Add actor/wp_title fields to WPCreated fixture payload

**Purpose**: The `WPCreated` handoff fixture in `tests/contract/test_handoff_fixtures.py` is missing required fields.

**Steps**:

1. Run the contract test:
   ```bash
   pytest tests/contract/test_handoff_fixtures.py -v --tb=long 2>&1 | head -60
   ```

2. Identify which fields are missing. Read the `WPCreated` event model:
   ```bash
   python -c "from spec_kitty_events import WPCreated; import inspect; print(inspect.getsource(WPCreated))"
   ```

3. Add `actor` and `wp_title` fields to the fixture payload in `test_handoff_fixtures.py`:
   ```python
   # Example (adjust field names/types to match actual model):
   WPCreated(
       mission_id="...",
       wp_id="WP01",
       actor="claude",         # add this
       wp_title="Test task",   # add this
       ...
   )
   ```

4. Run the test to confirm:
   ```bash
   pytest tests/contract/test_handoff_fixtures.py -v
   ```

**Files**: `tests/contract/test_handoff_fixtures.py`

**Validation**:
- [ ] Contract test passes with `actor` and `wp_title` fields present
- [ ] No production code changes needed for this subtask

---

## Subtask T030 — Remove vendored events tree if re-appeared

**Purpose**: The vendored copy of `spec_kitty_events` under `src/specify_cli/spec_kitty_events/` should not exist. The canonical source is the external PyPI package.

**Steps**:

1. Check if the directory exists:
   ```bash
   ls src/specify_cli/spec_kitty_events/ 2>&1
   ```

2. If it DOES NOT exist: this item is already resolved — skip and note in commit message.

3. If it EXISTS:
   - Confirm it is genuinely a vendored copy (not a legitimate internal module): check if it contains `__init__.py` with package metadata matching the `spec_kitty_events` PyPI package.
   - If confirmed vendored: `git rm -r src/specify_cli/spec_kitty_events/`
   - Run tests to confirm nothing imported from that path: `pytest tests/architectural/test_shared_package_boundary.py -v`

4. Run the architectural boundary test:
   ```bash
   pytest tests/architectural/test_shared_package_boundary.py -v
   ```

**Validation**:
- [ ] `src/specify_cli/spec_kitty_events/` does not exist after this subtask
- [ ] Architectural boundary test passes

---

## Subtask T031 — Add `# pydantic_model:` frontmatter to YAML codeblock in example fixture

**Purpose**: A YAML codeblock in a contract example fixture is missing the required `# pydantic_model:` frontmatter comment.

**Steps**:

1. Run the contract tests to identify which fixture is flagged:
   ```bash
   pytest tests/contract/ -v --tb=long 2>&1 | grep -A 10 "pydantic_model"
   ```

2. Locate the flagged fixture file and the YAML codeblock within it.

3. Add the `# pydantic_model: <ModelName>` comment as the first line of the YAML codeblock. The model name should match the Pydantic model that the example represents.

4. Run the contract tests to confirm:
   ```bash
   pytest tests/contract/ -v
   ```

**Files**: Contract example fixture YAML (as identified by test output)

**Validation**:
- [ ] The flagged contract test passes
- [ ] The `# pydantic_model:` comment is present in the correct position

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`

This WP can run in parallel with WP08 and WP09.

To start implementation:
```bash
spec-kitty agent action implement WP07 --agent claude
```

---

## Definition of Done

- [ ] All six tests listed in #1301 pass
- [ ] `test_daemon_intent_gate` passes
- [ ] `BuildRegistered` queued at init (test passes)
- [ ] `MissionOriginBound` queued when no WebSocket (test passes)
- [ ] `WPCreated` fixture has `actor` and `wp_title` fields (test passes)
- [ ] `src/specify_cli/spec_kitty_events/` does not exist
- [ ] YAML codeblock has `# pydantic_model:` frontmatter (test passes)

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Package version mismatch introduces new failures | Medium | Run `uv sync --frozen` first; don't change versions |
| Vendored events directory not present (already fixed) | Medium | Check first; skip T030 if absent |
| WPCreated model fields differ from expectation | Low | Read the model source before editing the fixture |

---

## Reviewer Guidance

1. Package version must NOT have changed (check `uv.lock` diff)
2. `src/specify_cli/spec_kitty_events/` must not exist in the commit
3. All six test IDs from #1301 must pass
</content>