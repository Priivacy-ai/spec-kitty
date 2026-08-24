---
work_package_id: WP01
title: Canonical session assessment
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
planning_base_branch: fix/setup-plan-auth-diagnostics-nonfatal
merge_target_branch: fix/setup-plan-auth-diagnostics-nonfatal
branch_strategy: Planning artifacts for this mission were generated on fix/setup-plan-auth-diagnostics-nonfatal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/setup-plan-auth-diagnostics-nonfatal unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Session assessment authority
history:
- at: '2026-08-24T00:00:00Z'
  actor: system
  action: Clarified two-dimensional evaluation evidence without tri-state authentication
- at: '2026-08-23T18:07:49Z'
  actor: system
  action: Prompt rewritten after post-tasks architecture review
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/auth/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/auth/token_manager.py
- src/specify_cli/readiness/auth.py
- tests/auth/test_token_manager.py
- tests/readiness/test_auth_probe.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3621
---

# Work Package Prompt: WP01 – Canonical session assessment

## Do This First: Load Agent Profile

Load `implementer-ivan` through the profile-load workflow before implementation. Read
the project charter and the Mission artifacts named below. Follow ATDD-first: the first
lane commit must be a failing test commit that is red on the planning base.

## Objectives & Success Criteria

Fix the information-loss defect at its source. `TokenManager` must expose typed,
invocation-local evaluation evidence with two separate dimensions: whether evaluation
completed and, only when it did, the Boolean usable-session verdict. Completed + usable
means authenticated; completed + unusable means logged out. Storage, decryption,
parsing, hot-summary materialization, or evaluation failure produces no auth verdict—it
is operational failure evidence, not an `unknown` authentication state.

Completion requires:

- expired access token + usable refresh token → completed assessment, usable session;
- readable empty/expired-refresh session → completed assessment, no usable session;
- storage or materialization failure → failed assessment with no session verdict;
- `is_authenticated` remains a compatible Boolean projection;
- readiness consumes the typed assessment and consults Teamspace detection only after a
  conclusive logged-out result;
- setup-plan consumers read the canonical assessment directly rather than treating that
  contextual readiness projection as bearer authority;
- queue-scope readers and network clients are never touched;
- no credential/session contents enter logs or diagnostics.

## Context & Constraints

Read:

- `.kittify/charter/charter.md` — canonical authority, ATDD-first, credential handling.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/spec.md` — US2,
  FR-002–FR-006, C-001/C-002/C-004/C-007.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/plan.md` — component 1.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/research.md` — decisions 1–2.
- `docs/adr/3.x/2026-04-19-1-cli-auth-uses-encrypted-file-only-session-storage.md`.

Current facts:

- `TokenManager.load_from_storage_sync()` catches storage exceptions and clears the
  session.
- `_materialize_session_from_storage_sync()` similarly collapses failure.
- `is_authenticated` consequently cannot distinguish absent from unreadable.
- `readiness.auth.probe_auth_status()` currently projects any evaluation exception into
  a false Boolean before Teamspace detection.

Do not edit auth storage formats, OAuth flows, manager singleton behavior, queue-scope
parsers, synchronization code, or setup-plan in this WP.

## Branch Strategy

- **Planning base branch**: `fix/setup-plan-auth-diagnostics-nonfatal`
- **Merge target branch**: `fix/setup-plan-auth-diagnostics-nonfatal`
- **Implementation command**: `spec-kitty agent action implement WP01 --agent <name>`
- Spec Kitty assigns the execution worktree from `lanes.json`. Do not select or create a
  worktree manually.
- Modify only the four `owned_files` paths.

## Subtasks & Detailed Guidance

### Subtask T001 – Write and commit rejecting assessment-provenance tests

**Purpose**: Pin the authority behavior before changing it.

**Steps**:

1. In `tests/auth/test_token_manager.py`, use the existing isolated storage fixtures or
   a production-faithful encrypted/file storage test double that distinguishes:
   - successful read returning no session;
   - successful read returning an expired-refresh session;
   - successful read returning expired access + usable refresh;
   - read/decryption/parsing failure;
   - hot-summary presence followed by materialization failure.
2. Assert `completed`, `usable_session`, and a stable non-secret reason for each case.
3. Assert `is_authenticated` is true only when assessment completed with a usable
   session, and false for conclusive absence and assessment failure.
4. In `tests/readiness/test_auth_probe.py`, assert failed assessment maps to the existing
   readiness `AuthStatus.UNKNOWN` and short-circuits without calling the Teamspace
   detector.
5. Make queue-scope readers and network/refresh surfaces raise if invoked.
6. Run these tests against the planning base and commit the failing evidence separately.

**Files**: the two owned test files.  
**Parallel?**: Fixtures in each test file are file-disjoint, but one red commit must
capture the complete contract.  
**Acceptance**: Tests fail because current storage failures collapse to false/logged out.

### Subtask T002 – Preserve and expose TokenManager session assessment

**Purpose**: Retain the truth where storage is first observed.

**Steps**:

1. Define a small immutable typed value in `token_manager.py`; use project conventions
   such as a frozen/slots dataclass with constructor invariants.
2. Record the initial load result without storing an exception object or sensitive text.
3. Update hot-summary materialization so failure produces a failed assessment rather
   than an indistinguishable empty state.
4. Add a no-network local assessment method/property that reports:
   - `completed=true, usable_session=true` under usable refresh-token semantics;
   - `completed=true, usable_session=false` for conclusive absence/expired refresh;
   - `completed=false, usable_session=None` for preserved load/materialization/evaluation
     failure.
5. Implement `is_authenticated` as the Boolean projection and retain its documented
   refresh-token semantics.
6. Keep `set_session()` and `clear_session()` transitions coherent: successful set
   clears prior assessment failure; explicit clear is conclusively logged out after
   successful deletion.

**Files**: `src/specify_cli/auth/token_manager.py`.  
**Parallel?**: No.  
**Notes**: Do not expose raw storage exceptions or add broad suppressions.

### Subtask T003 – Project the canonical assessment into readiness

**Purpose**: Ensure readiness contextualizes auth without becoming another authority.

**Steps**:

1. Replace the Boolean-first branch in `probe_auth_status()` with typed assessment.
2. Map completed + usable directly to `AuthStatus.AUTHENTICATED`.
3. Map assessment failure directly to the existing `AuthStatus.UNKNOWN`; do not consult
   Teamspace detection. This readiness value describes probe failure, not auth state.
4. Only for completed + no usable session, call the existing detector and preserve
   `LOGGED_OUT_IN_TEAMSPACE` versus `NOT_IN_TEAMSPACE` and normalized handle behavior.
5. Preserve the module's no-raise contract and lazy imports.
6. Update docstrings to name the canonical authority and exact resolution order.

**Files**: `src/specify_cli/readiness/auth.py`, `tests/readiness/test_auth_probe.py`.  
**Parallel?**: Starts after T002.  
**Notes**: Do not introduce queue-scope or SaaS-flag logic here.

### Subtask T004 – Run focused gates

Run:

```bash
uv run pytest -q tests/auth/test_token_manager.py tests/readiness/test_auth_probe.py
uv run ruff check src/specify_cli/auth/token_manager.py src/specify_cli/readiness/auth.py \
  tests/auth/test_token_manager.py tests/readiness/test_auth_probe.py
uv run mypy --strict src/specify_cli/auth/token_manager.py src/specify_cli/readiness/auth.py
```

Also run the existing auth storage and session-hot-path tests selected by imports or
failure output. Report pre-existing failures under the charter rule; do not green-wash
them or modify unowned files.

## Test Strategy

The decisive tests use storage behavior, not `_FakeTokenManager(is_authenticated=True)`.
No fixture may read the real home directory, call OAuth, or contact SaaS. Assert the
assessment-failure path with cold load and hot-summary materialization because either can
erase truth. Maintain direct Boolean compatibility tests for unaffected consumers.

## Risks & Mitigations

- **Risk**: public auth behavior changes broadly. **Mitigation**: Boolean compatibility
  remains explicit and all existing token-manager tests run.
- **Risk**: failed assessment persists after login. **Mitigation**: test successful
  `set_session`.
- **Risk**: sensitive exception text leaks. **Mitigation**: stable reason enums/strings.
- **Risk**: refresh is accidentally attempted. **Mitigation**: fatal refresh/network spies.

## Review Guidance

Reject if readiness reconstructs auth from queue scope, if assessment failure is inferred
only from an exception that TokenManager still swallows, if this WP introduces a public
tri-state authentication state machine, or if real storage cases are replaced by Boolean
mocks. Verify no new public import requires editing `auth/__init__.py`; if that becomes
necessary, stop because repository version-bump rules expand the scope.

## Activity Log

- 2026-08-23T18:07:49Z – system – Prompt rewritten after architectural remediation.
- 2026-08-24 – system – Clarified evaluation provenance versus Boolean auth verdict.

### Updating Status

Use `spec-kitty agent tasks move-task WP01 --to <status>`; status events are authoritative.
