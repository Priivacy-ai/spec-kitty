# Tasks: MissionStatus Write-Path Completion & Profile-Load Surface Remediation

**Mission**: `status-writepath-profile-surface-remediation-01KTB6AN`
**Branch**: `feature/status-writepath-profile-surface-remediation` (planning base = merge target)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Data model**: [data-model.md](./data-model.md)

Two file-disjoint workstreams → three execution lanes:
- **Lane A (#1667):** WP01 → WP02
- **Lane B-core (#1636):** WP03 → WP04 → WP06
- **Lane B-charter (#1636):** WP05 (independent)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Retain `MissionStatus` instance in `agent status emit` and route through `ms.transition()` | WP01 | |
| T002 | Preserve commit semantics via `ms.save()` / aggregate transactional path | WP01 | |
| T003 | Add `mission_slug` allowlist guard at `MissionStatus.load()` | WP01 | [P] |
| T004 | Unit test: slug guard (accented-Latin + `.isascii()`) | WP01 | [P] |
| T005 | Integration test: `agent status emit` routes through aggregate, behavior-preserving | WP01 | |
| T006 | Verify emitted event + CLI output identical to prior direct path | WP01 | |
| T007 | Extend parity ratchet fixture with a status **write** transition step | WP02 | |
| T008 | Assert CWD-parity of the write across main-checkout and lane-worktree | WP02 | |
| T009 | Anti-vacuity: corrupt write path → ratchet catches divergence | WP02 | [P] |
| T010 | Confirm CI registration covers the extended ratchet | WP02 | [P] |
| T011 | Implement `build_activation_aware_doctrine_service(repo_root)` factory | WP03 | |
| T012 | Construct inner `DoctrineService` + wrap with `PackContext.from_config` | WP03 | |
| T013 | Unit test: three-state activation filtering via factory | WP03 | [P] |
| T014 | Layer-safety test: factory import does not break `doctrine ← charter` | WP03 | [P] |
| T029 | Add glossary terms: *abstract base profile*, *activation chokepoint*, *activated vs available profile* (FR-019) | WP03 | [P] |
| T015 | `profile list`: filter `ProfileRegistry` rows by activated set (FR-011) | WP04 | |
| T016 | `profile list`: `--all` / `--show-available` annotated output (FR-012) | WP04 | |
| T017 | `profile show <id>`: full resolved definition render + `--json` (FR-013) | WP04 | |
| T018 | `profile show`: activation gate + `profile_not_activated` error (FR-014) | WP04 | |
| T019 | `profile show`: lineage Option A traversal + non-activated-parent warning (FR-015) | WP04 | |
| T020 | Unit tests: list filtering + NFR-001 byte-identity on unconfigured project | WP04 | [P] |
| T021 | Unit tests: show gating, not-found schema, abstract-parent warning | WP04 | [P] |
| T022 | `--all` bypass on `profile show` for inspection | WP04 | |
| T023 | Add scoped `_build_activation_aware_doctrine_service` in `charter/context.py` | WP05 | |
| T024 | Route only the `agent-profile:<id>` include branch through the wrapped service | WP05 | |
| T025 | Unit test: `--include agent-profile` inherits the activation gate | WP05 | [P] |
| T026 | Verify the other 5 `_build_doctrine_service` call sites are unchanged | WP05 | |
| T027 | Reconcile `ad-hoc-profile-load/SKILL.md`: point to `ask`/`advise`/`show`; resolve `hierarchy`/`init`/`create` | WP06 | |
| T028 | Doc/CLI parity guard test: every referenced `agent profile` subcommand is a registered command | WP06 | [P] |
| T030 | Cross-link the new `profile show` command surface in the skill steps | WP06 | |
| T031 | Verify reconciled skill references only implemented commands | WP06 | |

---

## Work Packages

### WP01 — Status write-surface wiring + slug guard (#1667 / FR-004, FR-007)
**Priority**: P1 · **Lane A** · **Depends on**: none · **Est.**: ~380 lines

**Goal**: Make the `MissionStatus` aggregate the sole entry point for status writes by routing `agent status emit` through `ms.transition()/.save()` (FR-004), and add a `mission_slug` allowlist guard at `load()` (FR-007). Behavior-preserving.

**Independent test**: `agent status emit` produces an identical event + output to the prior direct path; malformed slug is rejected with a typed error.

- [x] T001 Retain `MissionStatus` instance in `agent status emit` and route through `ms.transition()` (WP01)
- [x] T002 Preserve commit semantics via `ms.save()` / aggregate transactional path (WP01)
- [x] T003 Add `mission_slug` allowlist guard at `MissionStatus.load()` (WP01)
- [x] T004 Unit test: slug guard (accented-Latin + `.isascii()`) (WP01)
- [x] T005 Integration test: `agent status emit` routes through aggregate, behavior-preserving (WP01)
- [x] T006 Verify emitted event + CLI output identical to prior direct path (WP01)

**Risks**: touching the live write path — keep strictly behavior-preserving; `transition()` already delegates to the same transactional emitter. No change to `coordination/transaction.py`.

### WP02 — Parity ratchet over the write path (#1672 slice / FR-008)
**Priority**: P2 · **Lane A** · **Depends on**: WP01 · **Est.**: ~240 lines

**Goal**: Extend the existing CWD-invariance ratchet to cover the status **write** transition now routed through the aggregate.

**Independent test**: ratchet asserts identical write outcome from main-checkout and lane-worktree CWDs, and fails if the surface re-derives context.

- [x] T007 Extend parity ratchet fixture with a status **write** transition step (WP02)
- [x] T008 Assert CWD-parity of the write across main-checkout and lane-worktree (WP02)
- [x] T009 Anti-vacuity: corrupt write path → ratchet catches divergence (WP02)
- [x] T010 Confirm CI registration covers the extended ratchet (WP02)

**Risks**: shared P0 file owned by another contributor (C-008) — extend only, never weaken existing assertions.

### WP03 — Activation-aware doctrine service factory + glossary terms (#1636 / FR-010, FR-019)
**Priority**: P1 · **Lane B-core** · **Depends on**: none · **Est.**: ~260 lines

**Goal**: One shared factory wrapping the inner `DoctrineService` in the activation-aware `charter.resolver.DoctrineService`, used by `profile show` and `--include`. Also lands the FR-019 glossary terms **here** (dependency-free, before WP04's warning string) per the analyze I1 fix (DIR-032 vocab-before-code).

**Independent test**: factory returns a service whose `.agent_profiles` honors the three-state `activated_agent_profiles` contract; the three glossary terms are defined.

- [x] T011 Implement `build_activation_aware_doctrine_service(repo_root)` factory (WP03)
- [x] T012 Construct inner `DoctrineService` + wrap with `PackContext.from_config` (WP03)
- [x] T013 Unit test: three-state activation filtering via factory (WP03)
- [x] T014 Layer-safety test: factory import does not break `doctrine ← charter` (WP03)
- [x] T029 Add glossary terms: *abstract base profile*, *activation chokepoint*, *activated vs available profile* (FR-019) (WP03)

### WP04 — `profile list` (activation-aware) + `profile show` (#1636 / FR-011…015)
**Priority**: P1 · **Lane B-core** · **Depends on**: WP03 · **Est.**: ~480 lines

**Goal**: Activation-aware `profile list` (filter, not swap — preserve NFR-001) and a new activation-gated `profile show` with lineage Option A + abstract-base-profile warning.

**Independent test**: configured project lists only activated; unconfigured project unchanged; `show` gates non-activated ids; abstract-parent child resolves with a warning.

- [ ] T015 `profile list`: filter `ProfileRegistry` rows by activated set (FR-011) (WP04)
- [ ] T016 `profile list`: `--all` / `--show-available` annotated output (FR-012) (WP04)
- [ ] T017 `profile show <id>`: full resolved definition render + `--json` (FR-013) (WP04)
- [ ] T018 `profile show`: activation gate + `profile_not_activated` error (FR-014) (WP04)
- [ ] T019 `profile show`: lineage Option A traversal + non-activated-parent warning (FR-015) (WP04)
- [ ] T020 Unit tests: list filtering + NFR-001 byte-identity on unconfigured project (WP04)
- [ ] T021 Unit tests: show gating, not-found schema, abstract-parent warning (WP04)
- [ ] T022 `--all` bypass on `profile show` for inspection (WP04)

**Risks**: `profile list` default change — keep byte-identical for unconfigured projects (NFR-001).

### WP05 — `charter context --include` activation gate (#1636 / FR-016)
**Priority**: P2 · **Lane B-charter** · **Depends on**: none · **Est.**: ~220 lines

**Goal**: Route the `agent-profile:<id>` include branch through a scoped activation-aware service without changing the other 5 `_build_doctrine_service` call sites.

**Independent test**: `--include agent-profile:<non-activated>` is gated; other include kinds unaffected.

- [x] T023 Add scoped `_build_activation_aware_doctrine_service` in `charter/context.py` (WP05)
- [x] T024 Route only the `agent-profile:<id>` include branch through the wrapped service (WP05)
- [x] T025 Unit test: `--include agent-profile` inherits the activation gate (WP05)
- [x] T026 Verify the other 5 `_build_doctrine_service` call sites are unchanged (WP05)

### WP06 — Skill reconciliation + parity guard (#1636 / FR-017, FR-018)
**Priority**: P2 · **Lane B-core** · **Depends on**: WP04 · **Est.**: ~250 lines

**Goal**: Reconcile the `ad-hoc-profile-load` skill source so it references only real commands, and add a doc/CLI parity guard. (Glossary terms / FR-019 moved to WP03 per analyze I1.)

**Independent test**: parity guard passes; skill references resolve to registered commands.

- [ ] T027 Reconcile `ad-hoc-profile-load/SKILL.md`: point to `ask`/`advise`/`show`; resolve `hierarchy`/`init`/`create` (WP06)
- [ ] T028 Doc/CLI parity guard test: every referenced `agent profile` subcommand is a registered command (WP06)
- [ ] T030 Cross-link the new `profile show` command surface in the skill steps (WP06)
- [ ] T031 Verify reconciled skill references only implemented commands (WP06)

**Risks**: edit the **source** template (`src/doctrine/skills/...`), never the generated agent copies (C-006).

---

## Prompt Files

| WP | Prompt |
|----|--------|
| WP01 | [tasks/WP01-status-write-surface-wiring.md](./tasks/WP01-status-write-surface-wiring.md) |
| WP02 | [tasks/WP02-parity-ratchet-write-path.md](./tasks/WP02-parity-ratchet-write-path.md) |
| WP03 | [tasks/WP03-activation-aware-factory.md](./tasks/WP03-activation-aware-factory.md) |
| WP04 | [tasks/WP04-profile-list-and-show.md](./tasks/WP04-profile-list-and-show.md) |
| WP05 | [tasks/WP05-charter-context-include-gate.md](./tasks/WP05-charter-context-include-gate.md) |
| WP06 | [tasks/WP06-skill-reconciliation-and-glossary.md](./tasks/WP06-skill-reconciliation-and-glossary.md) |

## MVP

**WP03 + WP04** (the #1636 profile-load surfaces) deliver the most user-visible value and are independent of Lane A. Lane A (WP01/WP02) completes the #1667 ownership wiring.

## Parallelization

- Round 1 (no deps): **WP01, WP03, WP05** in parallel.
- Round 2: **WP02** (after WP01), **WP04** (after WP03).
- Round 3: **WP06** (after WP04).
