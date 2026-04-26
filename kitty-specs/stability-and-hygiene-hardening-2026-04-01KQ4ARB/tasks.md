# Tasks: Spec Kitty Stability & Hygiene Hardening (April 2026)

**Mission slug**: `stability-and-hygiene-hardening-2026-04-01KQ4ARB`
**Mission ID**: `01KQ4ARB0P4SFB0KCDMVZ6BXC8`
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Research**: [research.md](research.md)

**Branch contract**: starts on `main`; planning artifacts commit to `main`; final merge target is `main`.

## Mission summary

Eight dependency-aware work packages cover the full six-theme hardening pass.
Total: **50 subtasks**, average **~6 subtasks per WP** (200–500 line prompts).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Pin lane-planning data-loss regression and fix merge inclusion | WP01 |  |
| T002 | Make `spec-kitty merge --resume` resumable and bounded | WP01 |  |
| T003 | Post-merge index refresh — no phantom deletions | WP01 | [P] |
| T004 | Post-merge bookkeeping tolerates untracked `.worktrees/` and unrelated files | WP01 | [P] |
| T005 | Dependent-WP scheduler in lane planner | WP01 |  |
| T006 | Lane-specific test database isolation for parallel SaaS/Django lanes | WP01 | [P] |
| T007 | Provenance escape helper for `source_file` lines | WP02 | [P] |
| T008 | Path canonicalization + symlink guard for intake scanner | WP02 | [P] |
| T009 | Intake size-cap enforcement before full read | WP02 | [P] |
| T010 | Atomic write helpers for brief + provenance | WP02 | [P] |
| T011 | Missing vs corrupt distinction in intake reader | WP02 | [P] |
| T012 | Root consistency between scan and write | WP02 |  |
| T013 | `workspace/root_resolver.py` — single canonical-root resolver | WP03 |  |
| T014 | Wire status emit / charter / config writes through resolver | WP03 |  |
| T015 | Emit `planned -> in_progress` before worktree alloc; recoverable failure path | WP03 |  |
| T016 | Contract test: canonical root from inside a worktree | WP03 | [P] |
| T017 | Integration test: status emit on alloc failure | WP03 | [P] |
| T018 | Bare `next` does not advance state (no implicit success) | WP04 |  |
| T019 | Eliminate `unknown` mission state and `[QUERY - no result provided]` placeholder | WP04 |  |
| T020 | `execution_mode: planning_artifact` lane-skip path | WP04 |  |
| T021 | Review-claim transition emits `for_review -> in_review` | WP04 | [P] |
| T022 | `mark-status` accepts both bare and qualified WP IDs | WP04 | [P] |
| T023 | Dashboard / progress counters reflect approved / in-review / done correctly | WP04 | [P] |
| T024 | Validate `plan` mission's `mission-runtime.yaml` against runtime schema | WP04 | [P] |
| T025 | Resolved-version contract test for `spec-kitty-events` envelope | WP05 |  |
| T026 | `tests/contract/` as hard mission-review gate | WP05 |  |
| T027 | Architectural test: `spec_kitty_events.*` / `spec_kitty_tracker.*` public imports stable | WP05 | [P] |
| T028 | Architectural test: no `spec-kitty-runtime` production dep | WP05 | [P] |
| T029 | Downstream-consumer verification step for candidate releases | WP05 |  |
| T030 | ADR-2026-04-26-1: Contract pinning to resolved package version | WP05 | [P] |
| T031 | `scripts/snapshot_events_envelope.py` + dev workflow doc | WP05 | [P] |
| T032 | Centralized `AuthenticatedClient` in `src/specify_cli/auth/transport.py` | WP06 |  |
| T033 | Architectural test: no direct `httpx.Client` outside auth transport | WP06 | [P] |
| T034 | Token-refresh log dedup (≤1 user-facing line per invocation) | WP06 |  |
| T035 | `OfflineQueueFull` raise + drain helper | WP06 | [P] |
| T036 | Replay handles tenant/project collision deterministically | WP06 |  |
| T037 | Tracker bidirectional sync — bounded retries + structured failure | WP06 | [P] |
| T038 | ADR-2026-04-26-2: Centralized auth transport boundary | WP06 | [P] |
| T039 | Fail-loud uninitialized repo for spec/plan/tasks | WP07 | [P] |
| T040 | Branch-strategy gate for PR-bound missions | WP07 | [P] |
| T041 | Charter compact mode preserves directive IDs + section anchors | WP07 | [P] |
| T042 | Hide legacy `--feature` aliases in help output | WP07 | [P] |
| T043 | Local custom mission loader post-merge hygiene audit + fix or follow-up | WP07 | [P] |
| T044 | `issue-matrix.md` scaffold + populated traceability matrix | WP08 |  |
| T045 | E2E: dependent-WP planning lane merges without data loss | WP08 |  |
| T046 | E2E: uninitialized repo fails loud | WP08 | [P] |
| T047 | E2E: SaaS / sync flows under `SPEC_KITTY_ENABLE_SAAS_SYNC=1` | WP08 |  |
| T048 | E2E: package contract drift is caught before release | WP08 | [P] |
| T049 | ADR-2026-04-26-3: Cross-repo e2e as hard mission-review gate | WP08 | [P] |
| T050 | Wire mission-review skill to enforce e2e + `tests/contract/` gates | WP08 |  |

## Work Packages

### WP01 — Merge & Lane Dependency Safety

**Goal**: Land every approved commit from every lane (including `lane-planning`)
without silent omission; make merge resumable; refresh post-merge index without
phantom deletions; tolerate untracked `.worktrees/`; schedule dependent WPs into
lanes whose base includes the dependency; isolate parallel test databases.

**Backing FRs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, NFR-005.

**Independent test**: `spec-kitty-end-to-end-testing/scenarios/dependent_wp_planning_lane.py`
(WP08) plus this WP's unit and integration tests pass.

**Estimated prompt size**: ~480 lines (6 subtasks × ~75 lines).

**Dependencies**: none.

**Subtasks**:
- [ ] T001 Pin lane-planning data-loss regression and fix merge inclusion (WP01)
- [ ] T002 Make `spec-kitty merge --resume` resumable and bounded (WP01)
- [ ] T003 Post-merge index refresh — no phantom deletions (WP01)
- [ ] T004 Post-merge bookkeeping tolerates untracked `.worktrees/` and unrelated files (WP01)
- [ ] T005 Dependent-WP scheduler in lane planner (WP01)
- [ ] T006 Lane-specific test database isolation for parallel SaaS/Django lanes (WP01)

**Prompt**: [tasks/WP01-merge-lane-safety.md](tasks/WP01-merge-lane-safety.md)

---

### WP02 — Intake Security & Atomic Writes

**Goal**: Make `spec-kitty intake` safe under hostile / oversized / interrupted
inputs. Provenance escape, traversal/symlink block, size cap before full read,
atomic writes, missing-vs-corrupt distinction, single intake root.

**Backing FRs**: FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, NFR-003, NFR-004.

**Independent test**: WP02's unit + integration tests pass.

**Estimated prompt size**: ~430 lines (6 subtasks × ~70 lines).

**Dependencies**: none.

**Subtasks**:
- [ ] T007 Provenance escape helper for `source_file` lines (WP02)
- [ ] T008 Path canonicalization + symlink guard for intake scanner (WP02)
- [ ] T009 Intake size-cap enforcement before full read (WP02)
- [ ] T010 Atomic write helpers for brief + provenance (WP02)
- [ ] T011 Missing vs corrupt distinction in intake reader (WP02)
- [ ] T012 Root consistency between scan and write (WP02)

**Prompt**: [tasks/WP02-intake-security.md](tasks/WP02-intake-security.md)

---

### WP03 — Repo Authority + Status Emit Correctness

**Goal**: One resolver names the canonical mission repo from any CWD; status
emit, charter writes, and config writes route through it; emit `planned ->
in_progress` before any worktree allocation that could fail; recoverable
failure event on alloc failure.

**Backing FRs**: FR-013, FR-014.

**Independent test**: WP03's contract + integration tests pass.

**Estimated prompt size**: ~330 lines (5 subtasks × ~65 lines).

**Dependencies**: none.

**Subtasks**:
- [ ] T013 `workspace/root_resolver.py` — single canonical-root resolver (WP03)
- [ ] T014 Wire status emit / charter / config writes through resolver (WP03)
- [ ] T015 Emit `planned -> in_progress` before worktree alloc; recoverable failure path (WP03)
- [ ] T016 Contract test: canonical root from inside a worktree (WP03)
- [ ] T017 Integration test: status emit on alloc failure (WP03)

**Prompt**: [tasks/WP03-repo-authority.md](tasks/WP03-repo-authority.md)

---

### WP04 — Runtime `next` Correctness

**Goal**: `spec-kitty next` semantics align with the documented decision
algorithm. Bare calls do not advance. No `unknown` mission with
`[QUERY - no result provided]`. `planning_artifact` execution mode lands.
Review-claim transition is `for_review -> in_review`. `mark-status` accepts the
shape `tasks-finalize` emits. Dashboard counters correct. `plan` mission YAML
validates.

**Backing FRs**: FR-015, FR-016, FR-017, FR-018, FR-019, FR-020, FR-021.

**Independent test**: WP04's contract + integration tests pass.

**Estimated prompt size**: ~510 lines (7 subtasks × ~73 lines).

**Dependencies**: WP03 (uses the canonical-root resolver).

**Subtasks**:
- [ ] T018 Bare `next` does not advance state (no implicit success) (WP04)
- [ ] T019 Eliminate `unknown` mission state and `[QUERY - no result provided]` placeholder (WP04)
- [ ] T020 `execution_mode: planning_artifact` lane-skip path (WP04)
- [ ] T021 Review-claim transition emits `for_review -> in_review` (WP04)
- [ ] T022 `mark-status` accepts both bare and qualified WP IDs (WP04)
- [ ] T023 Dashboard / progress counters reflect approved / in-review / done correctly (WP04)
- [ ] T024 Validate `plan` mission's `mission-runtime.yaml` against runtime schema (WP04)

**Prompt**: [tasks/WP04-runtime-next.md](tasks/WP04-runtime-next.md)

---

### WP05 — Cross-Repo Package Contracts + Release Gates

**Goal**: Pin contract tests to the actually resolved version of
`spec-kitty-events`; make `tests/contract/` a hard mission-review gate; freeze
public imports of `spec_kitty_events.*` and `spec_kitty_tracker.*`; assert no
production dep on `spec-kitty-runtime`; require downstream-consumer
verification before stable promotion of any cross-repo package; record an ADR.

**Backing FRs**: FR-022, FR-023, FR-024, FR-025, FR-026.

**Independent test**: WP05's contract + architectural + integration tests
pass.

**Estimated prompt size**: ~470 lines (7 subtasks × ~67 lines).

**Dependencies**: none.

**Subtasks**:
- [ ] T025 Resolved-version contract test for `spec-kitty-events` envelope (WP05)
- [ ] T026 `tests/contract/` as hard mission-review gate (WP05)
- [ ] T027 Architectural test: `spec_kitty_events.*` / `spec_kitty_tracker.*` public imports stable (WP05)
- [ ] T028 Architectural test: no `spec-kitty-runtime` production dep (WP05)
- [ ] T029 Downstream-consumer verification step for candidate releases (WP05)
- [ ] T030 ADR-2026-04-26-1: Contract pinning to resolved package version (WP05)
- [ ] T031 `scripts/snapshot_events_envelope.py` + dev workflow doc (WP05)

**Prompt**: [tasks/WP05-package-contracts.md](tasks/WP05-package-contracts.md)

---

### WP06 — Sync / Offline Queue / Centralized Auth

**Goal**: A single `AuthenticatedClient` for sync / tracker / websocket;
token-refresh log dedup; `OfflineQueueFull` and drain helper; deterministic
replay collision handling; tracker bidirectional retry semantics; ADR.

**Backing FRs**: FR-027, FR-028, FR-029, FR-030, FR-031, NFR-007.

**Independent test**: WP06's architectural + integration tests pass; SaaS
e2e (WP08) uses the new transport.

**Estimated prompt size**: ~490 lines (7 subtasks × ~70 lines).

**Dependencies**: WP05 (auth transport sits at the cross-repo boundary).

**Subtasks**:
- [ ] T032 Centralized `AuthenticatedClient` in `src/specify_cli/auth/transport.py` (WP06)
- [ ] T033 Architectural test: no direct `httpx.Client` outside auth transport (WP06)
- [ ] T034 Token-refresh log dedup (≤1 user-facing line per invocation) (WP06)
- [ ] T035 `OfflineQueueFull` raise + drain helper (WP06)
- [ ] T036 Replay handles tenant/project collision deterministically (WP06)
- [ ] T037 Tracker bidirectional sync — bounded retries + structured failure (WP06)
- [ ] T038 ADR-2026-04-26-2: Centralized auth transport boundary (WP06)

**Prompt**: [tasks/WP06-sync-and-auth.md](tasks/WP06-sync-and-auth.md)

---

### WP07 — Governance / Context / Branch Guard Hygiene

**Goal**: Spec ceremony fails loudly outside an initialized repo; branch
strategy gate for PR-bound missions; charter compact view preserves directive
IDs and section anchors; legacy `--feature` aliases hidden but still accepted;
local custom mission loader post-merge hygiene audited and fixed or scoped.

**Backing FRs**: FR-032, FR-033, FR-034, FR-035, FR-036.

**Independent test**: WP07's contract + integration tests pass.

**Estimated prompt size**: ~360 lines (5 subtasks × ~72 lines).

**Dependencies**: none.

**Subtasks**:
- [ ] T039 Fail-loud uninitialized repo for spec/plan/tasks (WP07)
- [ ] T040 Branch-strategy gate for PR-bound missions (WP07)
- [ ] T041 Charter compact mode preserves directive IDs + section anchors (WP07)
- [ ] T042 Hide legacy `--feature` aliases in help output (WP07)
- [ ] T043 Local custom mission loader post-merge hygiene audit + fix or follow-up (WP07)

**Prompt**: [tasks/WP07-governance-hygiene.md](tasks/WP07-governance-hygiene.md)

---

### WP08 — Issue Traceability + Cross-Repo E2E Gates

**Goal**: Populate `issue-matrix.md` with a verdict for every issue from
`start-here.md`; add four e2e scenarios in `spec-kitty-end-to-end-testing`;
wire mission-review to enforce contract + e2e gates; record an ADR.

**Backing FRs**: FR-037, FR-038, FR-039, FR-040, FR-041, C-010.

**Independent test**: full e2e suite + the mission-review gate verifies the
matrix and the contract pass.

**Estimated prompt size**: ~510 lines (7 subtasks × ~73 lines).

**Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07.

**Subtasks**:
- [ ] T044 `issue-matrix.md` scaffold + populated traceability matrix (WP08)
- [ ] T045 E2E: dependent-WP planning lane merges without data loss (WP08)
- [ ] T046 E2E: uninitialized repo fails loud (WP08)
- [ ] T047 E2E: SaaS / sync flows under `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (WP08)
- [ ] T048 E2E: package contract drift is caught before release (WP08)
- [ ] T049 ADR-2026-04-26-3: Cross-repo e2e as hard mission-review gate (WP08)
- [ ] T050 Wire mission-review skill to enforce e2e + `tests/contract/` gates (WP08)

**Prompt**: [tasks/WP08-traceability-and-e2e.md](tasks/WP08-traceability-and-e2e.md)

---

## Lane / parallelization plan

The lane planner will compute final lane assignments. The intent:

- **Lane A**: WP01 → WP08 (merge / lane core path).
- **Lane B**: WP02 (intake) — independent from lane A.
- **Lane C**: WP03 → WP04 — sequential within the same lane (dependency
  edge declared in WP04 frontmatter).
- **Lane D**: WP05 → WP06 — sequential within the same lane (dependency
  edge declared in WP06 frontmatter).
- **Lane E**: WP07 (governance) — independent.

WP08 must run after WPs 01..07 land. The finalize-tasks step encodes this as
`depends_on`, not as a parallel lane. Per FR-005, dependent WPs go into a
lane whose base includes the dependency branch — WP04, WP06, WP08 lanes are
rebased onto their predecessors' tips before they begin.

## Branch strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Lane branches**: `kitty/mission-stability-and-hygiene-hardening-2026-04-01KQ4ARB-lane-<id>`
  (canonical naming includes `<mid8>`).
- **Lane base** for each lane is computed by the lane planner; dependent
  lanes rebase onto their predecessors' tips before starting.

## MVP scope recommendation

If the operator wants to ship a meaningful subset early, the MVP is **WP01 +
WP02 + WP03 + WP07**. Rationale: those four cover the highest-blast-radius
operator-facing failures (data loss in merge, intake hostile inputs,
canonical-repo writes, fail-loud uninitialized repo). WP04 follows as the next
slice once WP03 lands. WP05/WP06/WP08 close the loop around cross-repo
contracts, sync, and e2e gates.

For this mission, the operator has asked for the full set in one pass; the
MVP recommendation is informational only.
