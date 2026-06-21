# Tasks: Specify on Protected Primary + Branch-Protection Config

**Mission**: specify-protected-primary-coherence-01KVMBD6 | **Branch**: `fix/specify-protected-primary-coherence`
**Plan**: [plan.md](plan.md) (7 ICs) | **Spec**: [spec.md](spec.md) | **Design**: [research/protected-branch-carrier-decision.md](research/protected-branch-carrier-decision.md) · ADR `2026-06-21-1`

Tidy-First, P0-first. 7 WPs aligned to the 7 ICs, disjoint `owned_files` (shared surfaces
`commit_helpers.py`/`mission.py`/`accept.py`/`acceptance/__init__.py` linearized). Each behavior flip
is paired with its test edit in the same WP (landmines L1/L2 → WP04; patch targets P1/P2 → WP03; P3 → WP01).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create `ProtectionPolicy` value + `resolve(repo_root)` (.kittify config, default {main,master}) | WP01 | |
| T002 | Demote `protected_branches()` to delegate; reroute `safe_commit` internal reads; decide `evaluate` import topology (A1) | WP01 | |
| T003 | Verify-and-close #1828: hatch-symmetry regression pin via `is_protected()` | WP01 | |
| T004 | 4-row config resolution matrix unit tests (absent/explicit/empty/malformed) | WP01 | |
| T005 | Update `protected_target_fixtures.py` self-check (P3); confirm NFR-004 default | WP01 | |
| T006 | Extract the 5-function planning-commit pipeline → `commit_router.commit_for_mission` | WP02 | |
| T007 | New mission-aware spec-commit entrypoint (derives mission_slug; calls helper) | WP02 | |
| T008 | Actionable refusal error (materialize-then-retry / emit exact command) | WP02 | |
| T009 | Helper/entrypoint tests (placement, materialize, idempotency, #1718, negative) | WP02 | |
| T027 | Collapse the 3 inline commit tails (`:2443`/`:2500`/`:3937`) into `commit_for_mission` (#2056 de-god fold) | WP02 | |
| T028 | Register entrypoint in `cli/commands/__init__.py::register_commands` | WP02 | |
| T010 | Route `coordination/policy.py:214` through `ProtectionPolicy` (real chokepoint) | WP03 | [P] |
| T011 | Route `implement.py:59`; fix P1 mock target; add NFR-003 spy | WP03 | [P] |
| T012 | Route `tasks.py:882/916`; fix P2 mock targets | WP03 | [P] |
| T013 | NFR-003 spy test (resolve once; zero reads in `is_protected`/`evaluate`) | WP03 | |
| T014 | record-analysis (`mission.py:898`): materialize-then-retry (mission.py ⇒ WP02) | WP02 | |
| T015 | `accept.py:366`: materialize-then-retry | WP04 | |
| T016 | `acceptance._commit_acceptance_meta` (`:1202`): materialize-then-retry | WP04 | |
| T017 | REWRITE L1 `test_record_analysis_coord_worktree.py:292` (refusal→materialize) | WP02 | |
| T018 | REWRITE L2 `test_acceptance_support.py:519` (refusal→materialize) | WP04 | |
| T019 | Repo-wide single-resolver AST guard; exclude classification sets (same commit) | WP05 | |
| T020 | Verify guard collected into architectural gate; inline allowlist rationale | WP05 | |
| T021 | Re-point specify runbook to the new entrypoint; terminology guard | WP06 | |
| T022 | e2e kentonium3 repro with NEGATIVE materialization assertions | WP07 | |
| T023 | 3 sibling-site materialize-then-retry repros | WP07 | |
| T024 | US2 config-honoring (protected→worktree, unprotected→direct) | WP07 | |
| T025 | FR-006 hatch regression + extend #1718 create-window invariant (NFR-001) | WP07 | |
| T026 | NFR-004 default byte-identical + NFR-002 materialization bound | WP07 | |

## Work Packages

### WP01 — ProtectionPolicy foundation (IC-01) · MVP foundation

- **Goal**: the single boundary-resolved protection authority; everything depends on it.
- **Priority**: P0 foundation. **Dependencies**: none.
- **Independent test**: `pytest tests/git/test_protection_policy.py` — the 4-row matrix + hatch + default green.
- **Subtasks**:
  - [x] T001 Create `ProtectionPolicy` value + `resolve(repo_root)` (WP01)
  - [x] T002 Demote `protected_branches()`; reroute `safe_commit` internal; decide A1 import topology (WP01)
  - [x] T003 Verify-and-close #1828 hatch-symmetry pin (WP01)
  - [x] T004 4-row config resolution matrix tests (WP01)
  - [x] T005 Update `protected_target_fixtures.py` self-check (P3); NFR-004 default (WP01)
- **Risks**: subsume the `_remote_default_branch` read (NFR-003); empty-config vs remote-default trap; keep `test_safe_commit_import_boundary` green (A1).

### WP02 — Extract pipeline + spec-commit entrypoint + record-analysis (IC-02) · P0 MVP

- **Goal**: extract the canonical planning-commit pipeline (5 fns) out of `mission.py` into a reusable
  `commit_router.commit_for_mission`, build the new mission-aware spec-commit entrypoint on it, and convert
  record-analysis. Owns ALL `mission.py` edits (disjoint from WP04).
- **Priority**: P0 (the headline fix). **Dependencies**: WP01.
- **Independent test**: e2e — a protected-named primary completes the spec commit via the new entrypoint, spec lands on coord branch (narrow test here; full repro in WP07).
- **Subtasks**:
  - [x] T006 Extract 5-fn pipeline → `commit_for_mission` (WP02)
  - [x] T007 New mission-aware spec-commit entrypoint (WP02)
  - [x] T008 Actionable refusal error (WP02)
  - [x] T009 Helper/entrypoint tests + #1718 + negative variant (WP02)
  - [x] T027 Repoint mission.py's existing planning-commit callers (C-001) (WP02)
  - [x] T028 Register entrypoint in `cli/commands/__init__.py` (WP02)
  - [x] T014 record-analysis materialize-then-retry (WP02)
  - [x] T017 REWRITE L1 landmine (WP02)
- **Risks**: no parallel materializer AND no leftover duplicate (C-001, both directions); registration is in `cli/commands/__init__.py::register_commands` (NOT `specify_cli/__init__.py`); preserve #1718.

### WP03 — Input-reroute, non-deadlock sites (IC-03)

- **Goal**: route the protection *decision input* through `ProtectionPolicy` at the non-deadlock sites.
- **Priority**: P1. **Dependencies**: WP01.
- **Independent test**: `pytest tests/agent/test_implement_command.py tests/specify_cli/cli/commands/agent/test_move_task_guard.py` + the NFR-003 spy.
- **Subtasks**:
  - [x] T010 Route `coordination/policy.py:214` (WP03)
  - [x] T011 Route `implement.py:59`; fix P1; NFR-003 spy (WP03)
  - [x] T012 Route `tasks.py:882/916`; fix P2 (WP03)
  - [x] T013 NFR-003 spy test (WP03)
- **Risks**: P1/P2 mocks go silently vacuous if not re-pointed (the spy guards against this).

### WP04 — Close the deadlock class at accept/acceptance (IC-04)

- **Goal**: apply materialize-then-retry to `accept`/`acceptance._commit_acceptance_meta` via WP02's helper.
  (record-analysis moved to WP02 — it lives in mission.py.)
- **Priority**: P1 (completes the class). **Dependencies**: WP02, WP03.
- **Independent test**: the rewritten L2 test asserts materialize-then-retry + provenance, not refusal.
- **Subtasks**:
  - [x] T015 `accept.py:366` materialize-then-retry (WP04)
  - [x] T016 `acceptance._commit_acceptance_meta` materialize-then-retry (WP04)
  - [x] T018 REWRITE L2 landmine + provenance assertion (WP04)
- **Risks**: accept/acceptance commit-path blast radius; FR-009 provenance delivered by WP01's `:527` reroute; pair the flip with its test in THIS WP.

### WP05 — Single-resolver architectural guard (IC-05)

- **Goal**: enforce the single-authority property (FR-010 / #1868).
- **Priority**: P2. **Dependencies**: WP03, WP04.
- **Independent test**: the guard is green on the collapsed tree and red if a direct decision is reintroduced.
- **Subtasks**:
  - [x] T019 Repo-wide AST guard; exclude classification sets in same commit (WP05)
  - [x] T020 Verify gate-collection; inline allowlist rationale (WP05)
- **Risks**: repo-wide scan (NOT mission-diff-scoped); exclude `_WELL_KNOWN_INTEGRATION_BRANCHES` + `common_primary_branches`; architectural shard runs only in the heavy CI lane — pre-push runbook.

### WP06 — Specify runbook alignment (IC-06)

- **Goal**: re-point the specify prompt to the new entrypoint so runbook ↔ guard agree (SC-005).
- **Priority**: P2. **Dependencies**: WP02.
- **Independent test**: `pytest tests/architectural/test_no_legacy_terminology.py`; manual read confirms no refused command.
- **Subtasks**:
  - [x] T021 Re-point runbook; terminology guard; SOURCE-only (WP06)
- **Risks**: SOURCE template only (agent copies regenerate via upgrade); canonical "Mission" terminology.

### WP07 — Non-fakeable coverage (IC-07)

- **Goal**: prove the fix with assertions that fail if materialization is removed.
- **Priority**: P1 (acceptance). **Dependencies**: WP02, WP03, WP04.
- **Independent test**: the integration suite green on a protected-named primary; the negative assertions fail when the materialize call is stubbed out.
- **Subtasks**:
  - [x] T022 e2e kentonium3 repro + NEGATIVE assertions (WP07)
  - [x] T023 3 sibling-site repros (WP07)
  - [x] T024 US2 config-honoring (WP07)
  - [x] T025 FR-006 hatch + extend #1718 invariant (WP07)
  - [x] T026 NFR-004 byte-identical + NFR-002 bound (WP07)
- **Risks**: parallel-safe (hermetic `ProtectedTargetRepo`, no `-n0`); negative assertions are the anti-fakeable core.

## Dependencies & Lanes

```
WP01 ──┬── WP02 ──┬── WP04 ──┬── WP05
       │          │          │
       └── WP03 ──┘          └── WP07 (also needs WP02, WP03)
                  WP06 (needs WP02)
```

- WP01 is the foundation (start here — MVP).
- WP02 and WP03 parallelize after WP01.
- WP04 after WP02+WP03; WP05 after WP03+WP04; WP06 after WP02; WP07 after WP02+WP03+WP04.

## MVP

WP01 + WP02 deliver the headline P0 (specify deadlock closed via the new entrypoint). WP03–WP07 complete
the class, the configurability, the guard, the runbook, and the non-fakeable proof.
