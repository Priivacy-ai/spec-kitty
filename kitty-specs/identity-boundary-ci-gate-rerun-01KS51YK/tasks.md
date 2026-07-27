# Tasks: Identity-Boundary CI Gate (Rerun)

**Mission**: `identity-boundary-ci-gate-rerun-01KS51YK`
**Branch**: `mission/identity-boundary-ci-gate-rerun`
**Plan**: `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/plan.md`
**Spec**: `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/spec.md`

## Subtask Index

| ID    | Description                                                                          | WP   | Parallel |
|-------|--------------------------------------------------------------------------------------|------|----------|
| T001  | Author `.github/workflows/drift-detector.yml` in spec-kitty                          | WP01 |          |
| T002  | Add "Identity-Boundary CI Gate" README section to spec-kitty                         | WP01 |          |
| T003  | Local sanity: `uv run pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v` | WP01 |          |
| T004  | Validate workflow YAML syntactically (yq parse or python yaml.safe_load)             | WP01 |          |
| T005  | Create canonical-repo worktree for spec-kitty-events on a new lane branch            | WP02 |          |
| T006  | Author `.github/workflows/cross-repo-harness-tests.yml` in spec-kitty-events         | WP02 |          |
| T007  | Add "Identity-Boundary CI Gate" README section to spec-kitty-events                  | WP02 |          |
| T008  | Validate events workflow YAML and pinned-SHA correctness                             | WP02 |          |
| T009  | Create canonical-repo worktree for spec-kitty-saas on a new lane branch              | WP03 |          |
| T010  | Author `.github/workflows/canary-gate.yml` in spec-kitty-saas                        | WP03 |          |
| T011  | Add "Identity-Boundary CI Gate" README section to spec-kitty-saas (incl. secrets)    | WP03 |          |
| T012  | Validate saas workflow YAML; assert no Fly-app spin-up                               | WP03 |          |
| T013  | Author cross-repo manifests (spec-kitty.md, spec-kitty-events.md, spec-kitty-saas.md) | WP04 |          |

## Work Packages

### WP01: spec-kitty drift-detector workflow + README

**Goal**: Add `.github/workflows/drift-detector.yml` in this repo so every PR
runs the canonical-registry drift-detector test as a discrete, named
required-check job.

**Priority**: P0 — first WP, blocks WP04.

**Independent test**: After the WP file is in place, `uv run pytest
tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v` passes
locally, and the workflow file parses as valid YAML.

**Estimated prompt size**: ~250 lines.

**Included subtasks**:

- [ ] T001 Author `.github/workflows/drift-detector.yml` in spec-kitty (WP01)
- [ ] T002 Add "Identity-Boundary CI Gate" README section to spec-kitty (WP01)
- [ ] T003 Local sanity: `uv run pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v` (WP01)
- [ ] T004 Validate workflow YAML syntactically (yq parse or python yaml.safe_load) (WP01)

**Implementation sketch**:
1. Switch to lane worktree allocated by the runtime (per `lanes.json`).
2. Create `.github/workflows/drift-detector.yml` — single job named `drift-detector`, runs on `pull_request` + `push` to main.
3. Patch `README.md` with a new "Identity-Boundary CI Gate" section.
4. Run the pytest sanity check; capture output.
5. Validate YAML.

**Risks**: Job name must be `drift-detector` exactly (branch-protection contract).

**Dependencies**: none.

**Requirement refs**: FR-003, FR-004 (spec-kitty side), FR-005, FR-006, FR-009, NFR-003, NFR-004, C-001, C-007, C-008.

**Prompt**: `tasks/WP01-spec-kitty-drift-detector.md`

---

### WP02: spec-kitty-events cross-repo-harness-tests workflow + README

**Goal**: Add `.github/workflows/cross-repo-harness-tests.yml` in the
spec-kitty-events repo so every events PR clones the e2e harness at a
pinned SHA and runs the identity-boundary unit tests.

**Priority**: P0 — independent of WP01; blocks WP04.

**Independent test**: Workflow YAML parses; pinned SHA matches
`4d5206e08a30bf23ae4dabae532dc0e355078e16`; the two target test paths
exist at that SHA (verified at planning).

**Estimated prompt size**: ~280 lines.

**Included subtasks**:

- [ ] T005 Create canonical-repo worktree for spec-kitty-events on a new lane branch (WP02)
- [ ] T006 Author `.github/workflows/cross-repo-harness-tests.yml` in spec-kitty-events (WP02)
- [ ] T007 Add "Identity-Boundary CI Gate" README section to spec-kitty-events (WP02)
- [ ] T008 Validate events workflow YAML and pinned-SHA correctness (WP02)

**Implementation sketch**:
1. From canonical `Priivacy-ai/spec-kitty-events`, run `git worktree add ../spec-kitty-events-canary-gate -b mission/identity-boundary-ci-gate-events-rerun origin/main`.
2. In the worktree, author the workflow file (checkout events PR head + e2e at pinned SHA; `uv pip install -e` events over harness; pytest unit dirs).
3. Author README section with SHA-bump procedure.
4. Validate YAML.

**Risks**: Cross-repo `actions/checkout` needs `repository:` + `ref:` syntax. `uv pip install -e` from the cross-repo checkout requires correct working directory.

**Dependencies**: none (events repo independent of WP01).

**Requirement refs**: FR-002, FR-004, FR-005, FR-006, FR-008, NFR-002, NFR-004, C-001, C-002, C-006, C-007, C-008.

**Prompt**: `tasks/WP02-events-cross-repo-harness.md`

---

### WP03: spec-kitty-saas canary-gate workflow + README

**Goal**: Add `.github/workflows/canary-gate.yml` in the spec-kitty-saas
repo so every saas PR runs the identity-boundary canary in `--single`
mode against deployed-dev.

**Priority**: P0 — independent of WP01 and WP02; blocks WP04.

**Independent test**: Workflow YAML parses; secret-name contract documented; no Fly-app spin-up logic present.

**Estimated prompt size**: ~320 lines.

**Included subtasks**:

- [ ] T009 Create canonical-repo worktree for spec-kitty-saas on a new lane branch (WP03)
- [ ] T010 Author `.github/workflows/canary-gate.yml` in spec-kitty-saas (WP03)
- [ ] T011 Add "Identity-Boundary CI Gate" README section to spec-kitty-saas (incl. secrets) (WP03)
- [ ] T012 Validate saas workflow YAML; assert no Fly-app spin-up (WP03)

**Implementation sketch**:
1. From canonical `Priivacy-ai/spec-kitty-saas`, run `git worktree add ../spec-kitty-saas-canary-gate -b mission/identity-boundary-ci-gate-saas-rerun origin/main`.
2. Author the workflow file (checkout saas + e2e at pinned SHA; export env vars + secret; invoke canary script; upload artifacts).
3. Author README section (gate description, secret-name contract, SHA-bump procedure, branch-protection-admin note).
4. Validate YAML.

**Risks**: Secret `SPEC_KITTY_CANARY_TOKEN` may not yet exist in repo secrets. Workflow must fail clearly if unset — script already handles this. The README documents the secret-name contract.

**Dependencies**: none (saas repo independent of WP01, WP02).

**Requirement refs**: FR-001, FR-004, FR-005, FR-006, FR-007, NFR-001, NFR-004, C-001, C-002, C-003, C-004, C-006, C-007, C-008.

**Prompt**: `tasks/WP03-saas-canary-gate.md`

---

### WP04: Cross-repo manifests in mission directory

**Goal**: Document what landed in each repo, which lane branch was used,
which PR number was opened, and the exact required-check name a repo
admin must register on `main` after merge.

**Priority**: P1 — completes the planning surface, must run after
WP01-03 because it references their live PR URLs.

**Independent test**: Three manifest files exist under
`cross-repo-manifests/`, each with a PR URL and a check-name table row
matching `contracts/check-names.md`.

**Estimated prompt size**: ~220 lines.

**Included subtasks**:

- [ ] T013 Author cross-repo manifests (spec-kitty.md, spec-kitty-events.md, spec-kitty-saas.md) (WP04)

**Implementation sketch**:
1. After WP01-03 open their PRs and the PR numbers are known, author one manifest per repo under `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/`.
2. Each manifest: repo, lane branch, PR number+URL, required-check name (exact), files touched, LOC delta, admin action.
3. Commit to the mission planning branch (`mission/identity-boundary-ci-gate-rerun`).

**Risks**: Out-of-order execution (WP04 before any of WP01-03 finishes) yields a manifest that references "TBD". The implement-review loop will gate WP04 on WP01-03 completion via the `dependencies` field.

**Dependencies**: WP01, WP02, WP03 (in that the manifests reference the PR URLs).

**Requirement refs**: FR-005, FR-006, C-007, C-008.

**Prompt**: `tasks/WP04-cross-repo-manifests.md`

## Parallelization

- WP01, WP02, WP03 are independent of each other (different repos). They
  CAN run in parallel; we run them sequentially in `lane-a` to keep
  state coherent and to match the brief's parallelization posture
  ("much quieter now").
- WP04 strictly depends on WP01+WP02+WP03 completing (it references
  their PR URLs).

## MVP scope

WP01+WP02+WP03 ship the three workflow files. WP04 is the closing
documentation surface and is required for mission acceptance.
