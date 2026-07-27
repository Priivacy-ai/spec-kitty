# Tasks — Tooling Stability & Guard Coherence (01KTRC04)

**Branch**: `fixups/code-engine-stabilization` (planning base == merge target; PR held)
**Spec**: `spec.md` (FR-001..FR-009) · **Plan**: `plan.md` (10 ICs + D1-D3) · **Reviews**: `research/plan-review-*.md` (binding adjudications)

**Sequencing:** WP01 (ATDD suite) FIRST, no deps. WP02 (guard spine) depends on WP01; WP03 (awkward callers +
five-channel deletion), WP04 (ergonomics), WP05 (planning placement) ride the spine (dep WP02; WP03 also gates
the channel deletion). WP06/WP07/WP08/WP09 are independent parallel lanes. WP10 (ratchet+ADR) closes the spine
(deps WP03/WP04/WP05). IC-10 deep-review folded into per-WP Review Guidance (architect-alphonso on the guard
spine + DRG shape; reviewer-renata standard). Debby guardrails: capability grants wire ATOMICALLY with the
safe_commit change (WP02); never land a broken guard in a WIP commit; self-hosting escape hatch documented (WP03).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Protection-preserved invariants (direct-push blocked; non-placement protected-ref commits refused) — green TODAY, stay green | WP01 | [P] |
| T002 | Per-channel bypass repros (#1334 prefix + 4 other channels) — xfail(strict) until WP03 deletes them | WP01 | [P] |
| T003 | SC-6 protected-target e2e fixture skeleton (MUST contain .kittify/) | WP01 | |
| T004 | Caller census: all safe_commit/assert_not_protected_branch sites (17 confirmed) → census doc | WP02 | |
| T005 | core/commit_guard.py: GuardCapability + GuardVerdict + evaluate() (D1; __all__; unit tests) | WP02 | |
| T006 | safe_commit consumes CommitTarget + capability param (ADR Step 7); capability grants wired ATOMICALLY same commit | WP02 | |
| T007 | Convert the 13 mechanical callers to the CommitTarget path | WP02 | |
| T008 | IC-01 suite green + evaluate() unit coverage; no WIP-broken guard | WP02 | |
| T009 | Awkward caller: upgrade.py (no mission context → FLATTENED CommitTarget + upgrade_bookkeeping capability) | WP03 | |
| T010 | Awkward callers: decision_log.py (runtime_bridge boundary) + mission_creation.py (pre-spec) | WP03 | |
| T011 | Fold bool channels: allow_protected_branch_in_test_mode (incl =True production sites + ~8-module propagation) + allow_completed_op_on_protected_branch + op-record file-content exception | WP03 | |
| T012 | DELETE all five privilege channels + helpers + prefix constants; flip WP01 per-channel xfails | WP03 | |
| T013 | Self-hosting verification: this mission's own WP commits work post-change; escape hatch documented | WP03 | |
| T014 | Dir/bulk args: expand against worktree_root + explicit expansion report | WP04 | |
| T015 | --to-branch resolves INTO the CommitTarget (single destination authority, C-GUARD-3a) | WP04 | |
| T016 | Retire SPEC_KITTY_INFER_DESTINATION_REF (+const +its tests) | WP04 | |
| T017 | Regression tests #1820 + #1330 | WP04 | |
| T018 | resolve_placement_only(repo_root, mission_slug) projection in mission_runtime/resolution.py (shares internal helpers) | WP05 | |
| T019 | Thread placement through specify/plan commit paths + agent/mission.py planning paths | WP05 | |
| T020 | finalize-tasks reads the SAME resolution; retire _resolve_planning_branch meta.json authority | WP05 | |
| T021 | Guard refusal messages name the resolved destination; runbook/prompt text updated | WP05 | |
| T022 | SC-6 e2e (protected-target fresh mission, .kittify/ fixture) + #1784 step-by-step repro | WP05 | |
| T023 | analysis-findings/v1 frontmatter schema REUSING canonical severity vocabulary (no 9th model) | WP06 | [P] |
| T024 | record-analysis: verdict from validated frontmatter only; write-path loud failure; legacy read → unknown | WP06 | |
| T025 | Delete infer_verdict / infer_issue_counts substring logic after cutover | WP06 | |
| T026 | Update analyze command template (SOURCE doctrine) to emit the frontmatter; terminology guard | WP06 | |
| T027 | Regression tests C-FIND-1/2/3 (#1819: scary-prose→ready, critical-row→blocked, drift→loud) | WP06 | |
| T028 | MissionStatus.load consumes carried StatusSurfaceFragment | WP07 | [P] |
| T029 | status_transition consumes the fragment; delete local coord-path compositions | WP07 | |
| T030 | Extend parity ratchet: fragment-is-the-source assertion (#1821) | WP07 | |
| T031 | Identify + extract doctrine health-render helpers → _profile_health_render.py (pure move) | WP08 | [P] |
| T032 | Repoint doctor.py imports; verify byte-identical render output | WP08 | |
| T033 | Gates: ruff/mypy clean; doctor tests green | WP08 | |
| T034 | Provenance consumer inventory (2 confirmed: drg/merge.py:480, glossary/entity_pages.py:164) | WP09 | [P] |
| T035 | Provenanced[T] carrier replaces the object.__setattr__ sidecar in _tag_source | WP09 | |
| T036 | Migrate the consumers; mypy --strict clean on DRG path | WP09 | |
| T037 | Tests: typed provenance round-trip; zero getattr-provenance consumers (grep gate) | WP09 | |
| T038 | Tighten test_safe_commit_import_boundary once callers converted (#1355) | WP10 | |
| T039 | ADR 2026-06-03-2 addendum: resolver home, CommitTarget shape drift, Step 7 delivered | WP10 | |

---

## Work Packages

### WP01 — Protection-preserved suite (ATDD-first) — IC-01
- **Goal**: author the C-003 ratchet BEFORE any conversion: invariants that hold today and must stay green (direct-push blocked, non-placement protected commits refused), per-channel bypass repros (xfail-strict until WP03), and the SC-6 fixture skeleton.
- **Priority**: P0 (gates the spine) · **Dependencies**: none · **Independent test**: suite runs; invariants green; bypass repros xfail. (~300 lines)
- [x] T001 Protection-preserved invariants (WP01)
- [x] T002 Per-channel bypass repros, xfail(strict) (WP01)
- [x] T003 SC-6 fixture skeleton with .kittify/ (WP01)

### WP02 — Guard spine: commit_guard + safe_commit(CommitTarget) + mechanical callers — IC-02a
- **Goal**: the ADR Step-7 conversion. Census → SK policy module (D1) → safe_commit consumes CommitTarget + asserted capability (grants wired ATOMICALLY in the same commit) → 13 mechanical callers converted. Old channels still tolerated until WP03 (no WIP-broken guard).
- **Priority**: P0 · **Dependencies**: WP01 · **Independent test**: evaluate() unit tests + IC-01 suite green; mechanical callers on the new path. (~600 lines)
- [x] T004 Caller census doc (WP02)
- [x] T005 core/commit_guard.py policy module (WP02)
- [x] T006 safe_commit(CommitTarget)+capability, atomic grants (WP02)
- [x] T007 Convert 13 mechanical callers (WP02)
- [x] T008 Suite green; no WIP-broken guard (WP02)

### WP03 — Awkward callers + five-channel deletion — IC-02b
- **Goal**: convert the 4 awkward callers' first three (upgrade.py FLATTENED+capability; decision_log.py; mission_creation.py — agent/mission.py planning paths belong to WP05), fold the bool/file-content/env channels into GuardCapability, then DELETE all five privilege channels (strangler-ordered) and flip WP01's xfails. Self-hosting escape hatch documented.
- **Priority**: P0 · **Dependencies**: WP02 · **Independent test**: per-channel refusal tests green (former xfails); own-mission commits still work. (~550 lines)
- [x] T009 upgrade.py conversion (WP03)
- [x] T010 decision_log.py + mission_creation.py (WP03)
- [x] T011 Fold bool/file-content channels (WP03)
- [x] T012 Delete five channels; flip xfails (WP03)
- [x] T013 Self-hosting verification + escape hatch doc (WP03)

### WP04 — safe-commit ergonomics — IC-03
- **Goal**: dir/bulk args with expansion report; --to-branch resolves into the CommitTarget (single destination authority); retire SPEC_KITTY_INFER_DESTINATION_REF.
- **Priority**: P1 · **Dependencies**: WP02 · **Independent test**: #1820/#1330 repros pass. (~350 lines)
- [x] T014 Dir/bulk expansion + report (WP04)
- [x] T015 --to-branch → CommitTarget (WP04)
- [x] T016 Retire the env-var path (WP04)
- [x] T017 Regression tests (WP04)

### WP05 — Planning-phase placement threading — IC-04 (the catch-22 killer)
- **Goal**: `resolve_placement_only` projection (shared helpers, not a parallel resolver); thread specify/plan/finalize + agent/mission.py planning paths; retire the meta.json second authority; refusal messages name the destination; SC-6 e2e + #1784 repro.
- **Priority**: P1 · **Dependencies**: WP02 · **Independent test**: SC-6 — fresh mission on protected-target completes specify→finalize with artifacts on the resolved destination. (~600 lines)
- [x] T018 resolve_placement_only projection (WP05)
- [x] T019 Thread specify/plan + agent/mission.py paths (WP05)
- [x] T020 finalize-tasks same resolution; retire meta.json authority (WP05)
- [x] T021 Refusal messages + runbook text (WP05)
- [x] T022 SC-6 e2e + #1784 repro (WP05)

### WP06 — Structured findings carrier — IC-05
- **Goal**: analysis-findings/v1 frontmatter (REUSING the canonical severity vocabulary — no 9th model); verdict from structure only; write-path loud failure; legacy → unknown; substring logic deleted; analyze template updated.
- **Priority**: P1 · **Dependencies**: none (parallel lane) · **Independent test**: C-FIND-1/2/3 repros (#1819). (~500 lines)
- [x] T023 findings/v1 schema, severity reuse (WP06)
- [x] T024 Verdict from frontmatter; write-path-only loud failure (WP06)
- [x] T025 Delete substring logic (WP06)
- [x] T026 Analyze template (SOURCE doctrine) + terminology guard (WP06)
- [x] T027 C-FIND regression tests (WP06)

### WP07 — StatusSurfaceFragment threading — IC-06
- **Goal**: MissionStatus.load + status_transition consume the carried fragment; local compositions deleted; parity ratchet extended (#1821).
- **Priority**: P2 · **Dependencies**: none (parallel lane) · **Independent test**: parity assertion green; grep shows no local composition. (~300 lines)
- [x] T028 MissionStatus.load threading (WP07)
- [x] T029 status_transition threading + deletion (WP07)
- [x] T030 Parity ratchet extension (WP07)

### WP08 — doctor.py health-render extraction — IC-07
- **Goal**: pure extraction of doctrine health-render helpers beside _doctrine_health.py; byte-identical output; full split out of scope.
- **Priority**: P2 · **Dependencies**: none (parallel lane) · **Independent test**: identical render; doctor tests green. (~250 lines)
- [x] T031 Extract helpers (WP08)
- [x] T032 Repoint + identical-output verification (WP08)
- [x] T033 Gates (WP08)

### WP09 — DRG Provenanced[T] — IC-08
- **Goal**: typed carrier replaces the object.__setattr__ sidecar (D2); inventory-first; both consumers migrated; mypy --strict clean.
- **Priority**: P2 · **Dependencies**: none (parallel lane) · **Independent test**: grep-zero getattr-provenance; typed round-trip test. (~400 lines)
- [x] T034 Consumer inventory (WP09)
- [x] T035 Provenanced[T] carrier (WP09)
- [x] T036 Consumer migration + mypy strict (WP09)
- [x] T037 Tests + grep gate (WP09)

### WP10 — Spine closure: import-boundary ratchet + ADR addendum — IC-09
- **Goal**: tighten test_safe_commit_import_boundary (#1355); ADR 2026-06-03-2 addendum (home path, CommitTarget shape drift, Step 7 delivered).
- **Priority**: P2 · **Dependencies**: WP03, WP04, WP05 · **Independent test**: ratchet enforces the single entry point. (~250 lines)
- [x] T038 Tighten the import-boundary ratchet (WP10)
- [x] T039 ADR addendum (WP10)

---

## Recommended reviewer profiles (IC-10 folded — finalize-tasks assigns owners)
- **architect-alphonso** deep-review/sign-off: WP02+WP03 (capability model, no privilege-channel residue, mechanism/policy split), WP05 (single destination authority), WP09 (DRG public-shape change).
- **reviewer-renata**: standard review on all WPs. Incorrect doc paths are blocking.
- Failure modes to watch (from `research/plan-review-*.md`): rim-hardening recurrence, relaxation-as-coherence, GuardV2, verdict-parser brittleness, DRG ripple underestimate.
