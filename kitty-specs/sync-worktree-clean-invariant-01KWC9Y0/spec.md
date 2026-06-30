# Specification: Worktree-Clean Sync Invariant

**Mission:** `sync-worktree-clean-invariant-01KWC9Y0`
**Mission ID:** `01KWC9Y0YJN6PZE7D4X8VN9PDS`
**Type:** software-dev
**Created:** 2026-06-30
**Source:** GitHub issue [#2263](https://github.com/Priivacy-ai/spec-kitty/issues/2263) (split from #2262; verified by adversarial-squad code-trace at HEAD `4f457d6`)

## Purpose

Stop read-only sync, tracker, and status commands from silently dirtying the worktree and blocking mission commands.

When SaaS sync is enabled, background and read-like commands persist to `.kittify/config.yaml` as a side effect — identity completion on the emit path, and tracker `binding_ref` upgrades on read paths. Because `config.yaml` is not in the clean-tree allowlist, those writes leave the working tree dirty, and clean-tree-gated commands such as `record-analysis` then refuse to run with `DIRTY_WORKTREE`, blocking legitimate mission work. This mission makes those read paths side-effect-free and enforces a **worktree-clean invariant**, so an operator can trust that *reading* sync state never mutates their repo.

## User Scenarios & Testing

**Primary actor:** a developer or agent ("operator") running mission commands in a SaaS-sync-enabled checkout.

### Primary scenario (the behavior we are fixing)

1. The operator has SaaS sync enabled and a clean working tree.
2. They run a read-like / background command — e.g. `sync status --check`, `sync pull`, or a status-event emission.
3. They then run a clean-tree-gated command such as `record-analysis`.
4. **Expected:** `record-analysis` runs normally — the read commands left the tree untouched.
5. **Current (defective) behavior:** step 2 silently wrote `.kittify/config.yaml`, so step 3 refuses with `DIRTY_WORKTREE`.

### Acceptance scenarios

- **AS-1 (clean stays clean):** *Given* a clean SaaS-enabled checkout, *when* the operator runs any of { emit a status event, `sync status`, `sync pull`, `sync push`, `sync run`, background dossier sync trigger, lifecycle SaaS fan-out, `tracker status`, `tracker map list`, dashboard daemon tick }, *then* `git status --porcelain` is byte-identical before and after, and `.kittify/config.yaml` is unmodified.
- **AS-2 (legacy incomplete identity, first emit):** *Given* a checkout whose stored project identity has a persisted `project_uuid` but is missing deterministic fields such as `build_id`, *when* the operator emits a status event, *then* `.kittify/config.yaml` is not written, **and** the emitted event still carries a complete, stable project identity. If `project_uuid` itself is absent, the read path remains side-effect-free and must no-op or tell the operator to run `init`.
- **AS-3 (binding-ref upgrade available):** *Given* the tracker server returns a new/changed `binding_ref` during a read-like operation, *when* the operator runs `sync pull` / `sync status` / `map list`, *then* no file is written and the available upgrade is surfaced as a reported pending state.
- **AS-4 (real dirt still caught):** *Given* a genuinely uncommitted source edit, *when* the operator runs `record-analysis`, *then* it still refuses with `DIRTY_WORKTREE` (the guard is not weakened).
- **AS-5 (write-authorized boundary still persists):** *Given* an explicit, user-initiated write command (project init, explicit tracker bind, explicit apply-style command), *when* it runs, *then* persisting identity / binding-ref to `.kittify/config.yaml` is allowed and occurs.
- **AS-6 (sync disabled/unauthenticated):** *Given* SaaS sync is disabled or the operator is unauthenticated, *when* the read/background commands run, *then* they remain side-effect-free (no partial writes).
- **AS-7 (new command regression guard):** *Given* a newly added read/background command that violates the invariant, *when* the regression suite runs, *then* the parametrized no-dirty-tree test fails before merge.

### Edge cases

- A read command runs while the dashboard daemon is also active — neither path may write tracked files.
- A checkout where both dirt sources would fire on the same command (identity completion **and** a binding-ref upgrade) — the command must still leave the tree clean.
- Concurrent invocations (daemon + foreground) must not race a write into `config.yaml`.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Read-like and background commands — status-event emission; `sync status`, `sync pull`, `sync push`, `sync run`; background dossier sync trigger; lifecycle SaaS fan-out; `tracker status`, `tracker map list`; and the dashboard daemon tick — MUST NOT modify any tracked repository file (notably `.kittify/config.yaml`) as a side effect. | Required |
| FR-002 | Identity required by read/emit paths MUST be resolved **without persisting** to the repository, yielding a complete, usable identity when a persisted `project_uuid` exists. If `project_uuid` is absent, the read path MUST remain side-effect-free and surface a not-initialized/no-op result instead of minting identity. | Required |
| FR-003 | Persistence of project identity to `.kittify/config.yaml` MUST occur only at explicit write-authorized boundaries (project init and explicit apply-style commands), never as a side effect of a read/background command. | Required |
| FR-004 | Tracker `binding_ref` upgrades discovered during read-like operations MUST be surfaced as a **reported pending state** (e.g. a `pending_binding_upgrade` field on the result) rather than written; persistence happens only during an explicit bind/apply operation. | Required |
| FR-005 | An automated regression test MUST enforce the worktree-clean invariant (INV-1) across the full command surface in FR-001, failing if any covered command changes `git status --porcelain` on a clean checkout. | Required |
| FR-006 | The regression test MUST be **parametrized over the command surface** so that adding a new read/background command that violates the invariant fails the test. | Required |
| FR-007 | The existing clean-tree guard (the `record-analysis` `DIRTY_WORKTREE` refusal) MUST continue to refuse genuine uncommitted changes after the fix — the gate is not weakened, broadened, or allowlist-expanded. | Required |
| FR-008 | When SaaS sync is disabled or the operator is unauthenticated, the read/background commands MUST remain side-effect-free (no partial writes to tracked files). | Required |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | Identity resolved on read paths MUST be stable across repeated invocations within the same checkout, so deferring persistence does not change event identity. | Project identity (uuid, slug, node, build) is **identical across N≥2 consecutive** read/emit invocations — 0 variance. | Required |
| NFR-002 | Removing the side-effect write MUST NOT add user-perceptible latency to read commands. | Added wall-clock per command attributable to the change ≤ 50 ms (expected ≤ 0, since a write is removed). | Required |
| NFR-003 | New/changed code MUST meet the project quality bar. | `mypy --strict` passes, `ruff check` clean, ≥ 90% coverage on new/changed lines. | Required |
| NFR-004 | The no-dirty-tree regression test MUST be deterministic under the repo's parallel-test rules. | 0 flakes across 20 consecutive runs; daemon/real-port variants run serially (`-n0`). | Required |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | MUST NOT satisfy the invariant by allowlisting `.kittify/config.yaml` or `kitty-specs/**` in any clean-tree gate. The fix **removes** the write; it does not hide it. | Mandatory |
| C-002 | MUST NOT auto-run `doctor mission-state --fix` or any other repair/normalization as a side effect of read/sync paths. | Mandatory |
| C-003 | `.kittify/config.yaml` remains the canonical store for project identity and tracker binding config; only the *persistence boundary* (when/where the write happens) changes — not the storage location or schema. | Mandatory |
| C-004 | No change to on-the-wire event payloads or to SaaS server behavior is in scope. | Mandatory |
| C-005 | Existing complete-identity checkouts MUST continue to emit events with their already-persisted identity unchanged (backward compatible). | Mandatory |

## Success Criteria

| ID | Outcome |
|----|---------|
| SC-001 | After running any combination of read/background sync, tracker, and status commands on a clean checkout, the operator hits a **0% spurious `DIRTY_WORKTREE`** rate on subsequent clean-tree-gated commands. |
| SC-002 | **100%** of the covered command surface leaves the working tree byte-identical on a clean checkout (verified by the regression test). |
| SC-003 | **0 occurrences** of identity drift — the project identity emitted is identical across repeated read/emit invocations. |
| SC-004 | Genuine dirty trees are still caught — the clean-tree gate refuses **100%** of real uncommitted source edits (no regression). |
| SC-005 | A new read/background command that violates the invariant is **caught before merge** by the parametrized test. |

## Key Entities

- **Project identity record** (stored in `.kittify/config.yaml`): uuid, slug, node_id, build_id. States: *incomplete* / *complete*; *persisted* / *in-memory only*.
- **Tracker binding config** (stored in `.kittify/config.yaml`): `binding_ref`. States: *current* / *pending-upgrade*.
- **Worktree cleanliness state**: the `git status --porcelain` snapshot and the clean-tree gate's allowlist (`meta.json`, `.kittify/encoding-provenance/...`).
- **Write-authorization boundary**: the set of commands permitted to persist identity / binding config (project init, explicit tracker bind, explicit apply-style commands).

## Domain Language

- **Worktree-clean invariant (INV-1):** the guarantee that read-like and background commands never change `git status --porcelain`.
- **Write-authorized boundary:** a command explicitly permitted to persist identity / binding config to `config.yaml`.
- **Read-like / background command:** status-event emission, `sync status/pull/push/run`, background dossier sync trigger, lifecycle SaaS fan-out, `tracker status` / `map list`, dashboard daemon tick.
- **Clean-tree gate:** the `DIRTY_WORKTREE` refusal in `record-analysis` (and any structurally similar gate).
- *Out-of-vocabulary for this mission:* treating local "dashboard health" as proof of SaaS sync — that belongs to companion issue #2264, not here.

## Assumptions

- A side-effect-free identity-resolution path is expected to exist already (a read-only counterpart to the writing identity-completion call); the plan phase will confirm it and wire the read/emit call sites to it. *(Recorded per DIRECTIVE_003 so the chosen path is traceable.)*
- Identity completion is assumed **deterministic from checkout state**, satisfying NFR-001. If the plan phase finds it is not deterministic, the plan MUST either introduce a stable seed or persist once at a write-authorized boundary *before* first emit — it MUST NOT reintroduce a read-path write to `config.yaml`.
- The covered command surface in FR-001 is the canonical starting list; under the confirmed **comprehensive, test-driven** scope, the parametrized test may surface additional sibling paths that also write `config.yaml`, and those are in scope to fix.

## Dependencies & Sequencing

- **No blocking dependencies.** This mission is independently shippable (Phase 1).
- **Blocks #2262** — that issue's "dry-run is inert" acceptance criterion depends on this mission's INV-1.
- Companion **#2264** (success-reporting honesty) is independent and may proceed in parallel.

## Out of Scope

- Historical mission import into the SaaS projection (#2262).
- Success-reporting honesty / new `sync status --check` fields / dashboard state cells (#2264).
- Any change to SaaS server-side materialization or event schemas.
