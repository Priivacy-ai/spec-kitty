# Mission Specification: Execution-Context Unification

**Mission ID**: 01KTPKSTQVPMFXEN413XSMDP24
**Slug**: execution-context-unification
**Type**: software-dev
**Target + coordination branch**: fixups/code-engine-stabilization (single-branch / flattened topology)
**Parent**: #1666 (execution-state & context domain-boundary redesign) · advances #1619
**Drains (intake)**: #1814, #1816, #1789 (both halves), #1071, #1062, #1572, #1737, #1357, #1735, #1771, #1736, #1770, #1764 · adjacent: #1815

## Purpose

Structurally **drain the coord-vs-primary split-brain class**: Spec Kitty command surfaces each independently re-resolve where a mission's state, branch, status, artifacts, and prompts live, so the primary checkout and the coordination branch drift apart. Implement the ratified #1619/#1666 design for these seams — one resolved `MissionExecutionContext` threaded through every surface, with status/durable state owned by Mission-Management behind an OHS facade — so the divergence becomes structurally impossible, not patched per-symptom. This mission dogfoods a **flattened single-branch topology** (landing = coordination = the feature branch) as the immediate de-risking, while building the context unification as the durable fix.

## User Scenarios & Testing

**Primary actor:** an operator/agent running a mission lifecycle (and the maintainers draining the bug queue).

- **Scenario A — one source of truth:** Any command (`specify`/`plan`/`tasks`/`finalize`/`analyze`/`implement`/`review`/`merge`/`retrospect`) asks "where does this mission's state/branch/status live?" and gets the **same answer** regardless of CWD (primary checkout or lane/coord worktree). *Success:* the parity ratchet (FR-011) shows identical state from both CWDs.
- **Scenario B — the dogfood that failed:** `record-analysis` (#1814) and `implement`-claim (#1816) no longer deadlock/stall on coord-vs-primary artifact placement — they resolve via the context. *Success:* the paused mission 01KTNWFC's blockers do not reproduce.
- **Scenario C — runtime doesn't corrupt git ops:** sync daemons / dashboard (#1789, #1062) do not re-materialize tracked status mid-`rebase`/`reset`. *Success:* a long rebase on a mission branch completes without status-file clobber.
- **Edge:** a flattened-topology mission (no separate coord branch) runs the full lifecycle end-to-end with no split.

## Functional Requirements

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-001 | Grow the canonical **`MissionExecutionContext`** as a **doc-09 fragment / op-composite** (NOT a flat field bag) — resolved once, on the existing `mission_runtime.ExecutionContext` substrate. Fragments: identity (`mission_id`, `mid8` — derived **once**), branch/ref (`target_branch`, `coordination_branch`, `destination_ref` = ADR-2026-06-03-2 *CommitTarget*), workspace (`primary_root`, `current_cwd`, `coord_worktree`, `execution_workspace`, `allowed_command_cwd`), status-surface (`status_read_dir`, `status_write_dir`), artifact-placement, prompt-source (`prompt_source_dir`). An op assembles only the fragments it needs. | #1619 / doc-09 | Draft |
| FR-002 | Route **all command surfaces** through the context — no command independently re-derives mission state/branch/status/prompt paths. Collapse the duplicate resolvers (read-path `candidate_feature_dir_for_mission` → `_read_path_resolver`; two worktree-pointer parsers → one). | #1619/#1666 | Draft |
| FR-003 | **Adopt** the existing Mission-Management OHS facade (`status/aggregate.py:MissionStatus`): route the **remaining raw primary/coord status readers** through it (esp. `status_transition._identity_for_request` #1737). Facade is not built here — it exists; this is strangle/adoption. | #1666/#1667 | Draft |
| FR-004 | **Adopt** a single **artifact-placement invariant** at the two failing sites — `implement._ensure_planning_artifacts_committed_git` (#1816) and `record-analysis` (#1814) resolve placement via the context's artifact-placement fragment, not independent primary/coord logic. | #1814, #1816 | Draft |
| FR-005 | Runtime status writers **never re-materialize tracked status during a git op** (git-op guard on `materialize_if_stale`). | #1789 (git-op half), #1062 | Draft |
| FR-006 | Reconcile **retrospect** read/write to the canonical surface (no primary-checkout reads; no gitignored writes). | #1735, #1771 | Draft |
| FR-007 | Reconcile **merge** coord-topology seams (PATH/env, baking step, mixed JSONL). | #1736, #1770 | Draft |
| FR-008 | Status **visibility parity** primary↔coord (#1572); fix parallel coord-path derivation in `status_transition` (#1737); lock-serialize `CoordinationWorkspace.resolve` (#1357). | #1572,#1737,#1357 | Draft |
| FR-009 | Make `analysis-report` staleness keying + `record-analysis` **context-aware** (no false-stale; no coord-residue deadlock). | #1764, #1814 | Draft |
| FR-010 | (adjacent) Resolve the **bulk-edit/occurrence-map mechanism gap**: either extend the map to model multi-path structural moves, or scope `bulk_edit` to terminology + provide a separate reference-integrity gate. *(Decide in plan; fold-in confirmed.)* | #1815 | Draft |
| FR-011 | **Parity ratchet (regression guard):** **EXTEND** the existing `tests/architectural/test_execution_context_parity.py` (1,323 LOC) — do NOT fork a second parity test (would be a C-005 parallel-mechanism violation). Add dual-CWD assertions (primary vs lane/coord) across `specify → plan → tasks → analyze → implement → review → status` and a **flattened-topology synthetic fixture** so C-001 is *proven*, not just configured. | #1619/#1672 | Draft |
| FR-012 | Close the **missed seams** the read of the codebase surfaced: derive `mid8` and `target_branch` from a **single source** (context, never recomputed); route `prompt_source_dir` through the context; replace the `_find_feature_directory` **silent fallback** to the primary checkout with a **structured error** (no silent fallback, per the C-009 selector rule); make `materialize_if_stale` staleness keying **context-aware** (no false-stale across CWDs). | #1764, debugger seam scan | Draft |
| FR-013 | Delete the **5 dead `coordination/status_service.py` symbols** (`EventLogWriteTarget`, `StatusContractError`, `StatusReadSource`, `append_event_log_batch`, `read_wp_lane_actor`) — **strangler-ordered** (after consumers are on the facade), not migrated. | #1622/#391 | Draft |
| FR-014 | **Two validated background-process fixes** (squad-validated; #1789 is two processes, not one): **(a) Dashboard** [→ dashboard WP] must stop writing tracked `status.json` as a side-effect of reads — its handlers call the *writing* `materialize()` (`reducer.py`, unguarded) on every kanban request; switch to the read-only `materialize_snapshot` and honour the git-op guard, so no background **read** writes tracked status. **(b) Sync-daemon singleton** [→ daemon WP] re-fix — enforce **one daemon per host/auth-scope** keyed on `DaemonOwnerRecord` identity (auth-scope/queue), reaping stale `run_sync_daemon` orphans at the `ensure_sync_daemon_running` spawn path (scoped by executable/auth-identity). NOT a per-action context — the daemon is detached/missionless at startup. | #1789 (dashboard clobber **and** daemon leak), #1071 | Draft |
| FR-015 | **Collapse the duplicate daemon-lifecycle reapers** (C-005/NFR-005): the three sync orphan-reapers — `owner.is_orphan`/`list_orphan_records`, `orphan_sweep.sweep_orphans`, `daemon.scan_sync_daemons`/`cleanup_orphan_sync_daemons` (~390 LOC) — collapse to **one** canonical reaper keyed on `DaemonOwnerRecord`; dedup the duplicated `_is_process_alive` + daemon-health-probe shared across `sync/` and `dashboard/lifecycle.py`. The single reaper is what FR-014(b) wires into the spawn path. | reducer-randy validation / #1071 | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | No new parallel mechanism (C-005). | Extends the existing execution-state resolver; static check / review confirms one resolution path. | Draft |
| NFR-002 | Code quality. | `ruff` + `mypy` zero issues on changed paths; `tests/architectural/` (terminology, shared-package-boundary) pass. | Draft |
| NFR-003 | Determinism / no flakiness. | Parity ratchet is deterministic across repeated runs and both CWDs. | Draft |
| NFR-004 | Alignment. | Conforms to ADRs 2026-06-03-1/2/3 (domain model; ExecutionContext-owner + CommitTarget; Effector/Actor) + 2026-06-07-1 (lane FSM) + doc-09 fragment model. The context **is** the ADR-2026-06-03-2 ExecutionContext-owner; `destination_ref` **is** its CommitTarget — reuse those names, coin none. | Draft |
| NFR-005 | Net subtraction. | The unification collapses ~500–650 LOC of parallel resolvers + deletes 5 dead symbols (FR-013). Changed-path LOC should trend **down**, not up. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | **Single-branch / flattened topology** for this mission: landing = coordination = `fixups/code-engine-stabilization`; no separate `coordination_branch` (immediate de-risk against #1816). | Active |
| C-002 | **No parallel mechanisms** (C-005 carryover): extend the existing execution-state strangler (`feat/execution-state-strangler` / mission 01KTG6P9 / #1666 slice), do not fork a second context resolver. | Active |
| C-003 | Honour the ratified #1619/#1666 ADRs and the Terminology Canon. | Active |
| C-004 | Strangler discipline: convert seams one at a time behind the facade; never break the lifecycle mid-conversion. | Active |

## Success Criteria
- **SC-1:** Parity ratchet green — identical mission state from primary and lane/coord CWD; zero split; clean trees.
- **SC-2:** The paused-mission blockers (#1814 record-analysis, #1816 implement-claim) do not reproduce on a fresh mission.
- **SC-3:** Each folded issue's repro passes (or is structurally precluded) after the context is threaded through its seam.
- **SC-4:** Static/review check confirms **one** mission-state resolution path (no parallel resolver) — C-005 upheld.
- **SC-5:** A long `git rebase` on a mission branch completes with no daemon/dashboard status-file clobber (#1789 git-op half).
- **SC-6:** (a) the dashboard serves kanban requests with **no tracked `status.json` write** (read-only snapshot) — a long `git rebase` with the dashboard live does not clobber status; (b) across multiple interpreters/sessions on one host, exactly **one** sync daemon runs per host/auth-scope and stale `run_sync_daemon` orphans are reaped at spawn (#1789 / #1071).
- **SC-7:** Exactly **one** daemon-lifecycle reaper remains (the three are collapsed) and `_is_process_alive`/health-probe is defined once — `rg` finds no duplicate reaper/liveness implementations across `sync/` + `dashboard/` (C-005; FR-015).

## Key Entities
- **`MissionExecutionContext`** — the single resolved per-mission context, composed as a **doc-09 fragment / op-composite** on the `mission_runtime.ExecutionContext` substrate (the unification core). It is the ADR-2026-06-03-2 **ExecutionContext-owner**.
- **`destination_ref` (CommitTarget)** — the one ref planning artifacts + status resolve to (ADR-2026-06-03-2 CommitTarget); eliminates the primary↔coord split.
- **`MissionStatus` aggregate + OHS facade** (`status/aggregate.py`, **already exists**) — Mission-Management-owned status read/write surface; remaining raw readers are strangled onto it (FR-003).
- **`CoordinationWorkspace`** — coord resolution (to be lock-serialized #1357 + context-fronted).
- **Duplicate resolvers to collapse** — `candidate_feature_dir_for_mission` (→ `_read_path_resolver`), `workspace/root_resolver` worktree parser (→ `core/paths`), `status_transition._identity_for_request` (→ resolved surface).
- **Command surfaces** — specify/plan/tasks/finalize/analyze/implement/review/merge/retrospect (the consumers to strangle).
- **Dashboard** — the actual background tracked-status writer (`materialize()` on read); fixed to a read-only snapshot (FR-014a). **Sync daemon** — machine-global, missionless; not a status writer — its fix is the singleton/reaper (FR-014b, one-per-host/auth-scope). The two are distinct processes (#1789 conflated them).

## Assumptions
- Intake corpus is authoritative: #1814, #1816, #1815, #1666 (+ its open same-class children listed above), #391 (#1622/#1623/#1624 dead `status_service` symbols).
- The existing execution-state strangler work is the substrate to extend — **verified** by the squad: `mission_runtime.ExecutionContext` + `resolve_action_context` exist and are incomplete; `MissionStatus`/OHS facade exists; the parity ratchet exists (1,323 LOC); doc-09 ratifies the fragment model. See `research.md`.
- **Research complete** (debugger-debby / reducer-randy / architect-alphonso): seam inventory (7 resolvers / Clusters A–E + 6 missed seams), duplication (~500–650 LOC) + 5 dead symbols, and design conformance (FR-001 re-anchored on doc-09; FR-011 extends not forks; FR-003/004 are adoption) are recorded in `research.md` and folded into the FRs above.

## Out of Scope
- The full Beads state backend (#1168, 3.3.0) — a later replacement, not this unification.
- Re-running the paused 01KTNWFC mission (resumed separately once this lands).
