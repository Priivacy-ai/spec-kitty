---
description: "Work package task list — Primary & Merge Vocabulary Disambiguation (Track 1)"
---

# Work Packages: Primary & Merge Vocabulary Disambiguation (Track 1)

**Inputs**: Design documents from `kitty-specs/primary-merge-vocabulary-01KXP11C/`
**Prerequisites**: plan.md, spec.md (squad-hardened), research.md, occurrence_map.yaml (bulk_edit), quickstart.md

**Tests**: Behavior-invariance is the acceptance property — existing suites stay green; the only NEW test work is the FR-007 compat/behavior red-first and an optional non-Sense-C alias-ban guard (WP06).

**Bulk-edit**: `change_mode: bulk_edit`. Every WP diff MUST comply with `occurrence_map.yaml` per-category actions. `is_primary_artifact_kind` and all serialized/Sense-C tokens are EXEMPT/DEFER — do not touch.

---

## Work Package WP01: Glossary sense entries (Priority: P1) 🎯 MVP

**Goal**: One canonical glossary entry per sense (4 primary + 3 merge) in `docs/context/`, using the existing per-term table format with `Do NOT use when` + cross-links. Extend the existing "Primary Branch" entry (do not duplicate).
**Independent Test**: `docs/context/orchestration.md` + `execution.md` each read with distinct, non-overlapping entries for every sense; description-length + anti-sprawl gates green.
**Prompt**: `/tasks/WP01-glossary-sense-entries.md`
**Requirement Refs**: FR-001, FR-002, FR-004

### Included Subtasks

- [x] T001 Add `primary` Sense-A (PRIMARY partition) + Sense-D (target ref) entries to `docs/context/orchestration.md` (append-only block — C-006)
- [x] T002 Add/extend `primary` Sense-B "Primary Branch" cross-refs (entry exists) + confirm Sense-C "repository root checkout" entry in `docs/context/execution.md` (prose only; symbol stays Track 2)
- [x] T003 Add `merge` Sense 1/2/3 entries (lane consolidation / branch integration / publish to origin) to `docs/context/orchestration.md`
- [x] T004 Wire `Related terms` cross-links + `Do NOT use when` guidance across all new entries

### Dependencies
- None (starting package).

### Risks & Mitigations
- Hot-file collision with in-flight `mission-step-authority-01KXNZMT` on `orchestration.md` (C-006) → keep additions **append-only** blocks; coordinate land order.

---

## Work Package WP02: Prose / help / docstring disambiguation sweep (Priority: P1)

**Goal**: Reword conflating surfaces to name the specific sense; condense CLAUDE.md's 3 warnings into one glossary pointer that STILL names the partition-vs-branch footgun.
**Independent Test**: `spec-kitty merge --help` + accept→merge help read unambiguously; the ADR paragraph + CLAUDE.md no longer conflate senses; terminology guard proven to execute (#2701); no exempt string-literal test red.
**Prompt**: `/tasks/WP02-prose-help-docstring-sweep.md`
**Requirement Refs**: FR-003, FR-011

### Included Subtasks

- [x] T005 Clarify `cli/commands/merge.py` `--help`/docstrings (Sense 1/2 wording; strategy literals unchanged)
- [x] T006 Clarify `cli/commands/agent/mission_accept_merge.py` accept→merge help (`--target`/`--push`/`--keep-branch`)
- [x] T007 Clarify the conflating paragraph in `docs/adr/3.x/2026-06-24-2-write-branch-resolution-primary-anchor.md` (sentence-level rewrite — mixed-sense)
- [x] T008 Condense `CLAUDE.md`'s 3 defensive warnings → 1 glossary pointer naming the footgun (FR-011)
- [ ] T009 Clarify merge-step doctrine prompts (watch C-006 collision on `mission-steps/`)

### Dependencies
- Depends on WP01 (entries must exist to cross-reference).

### Risks & Mitigations
- A `--help` string asserted byte-exact in a test → update assertion in lockstep or treat as exempt (edge case).

---

## Work Package WP03: Glossary-infrastructure cleanup (Priority: P2)

**Goal**: One prose-glossary home — repoint stale `glossary/README.md` and fold legacy `glossary/` prose into `docs/context/`.
**Independent Test**: `glossary/README.md` has no dead `glossary/contexts/` links; legacy prose relocated under `docs/context/`; `relative_link_fixer --check` clean; `.github` symlinks intact.
**Prompt**: `/tasks/WP03-glossary-infra-cleanup.md`
**Requirement Refs**: FR-005, FR-006

### Included Subtasks

- [x] T010 Repoint `glossary/README.md` context links → `docs/context/` (FR-005)
- [x] T011 Relocate `glossary/historical-terms.md` + `glossary/naming-decision-tool-vs-agent.md` → `docs/context/` per occurrence_map `moves[]` (FR-006)
- [x] T012 Update inbound references + `docs/context/index.md`; fix `../` relative links; `git add -f` any `.github` symlinks

### Dependencies
- Depends on WP01 (canonical entries exist to point at).

### Risks & Mitigations
- Moving docs breaks relative links → run `relative_link_fixer --check`; downstream consumers #1341/#648 (note, no change required here).

---

## Work Package WP04: `resolve_primary_branch` consolidation (Priority: P2)

**Goal**: One canonical resolver behavior. Resolve the delegating-shim compat re-export and the recommendation re-implementation (fold-with-bias-param or scope-out with rationale). Name unchanged (D1).
**Independent Test**: one real `resolve_primary_branch` def; `tasks.py.__all__` + `test_tasks_compat_surface` updated in lockstep; `_resolve_primary_branch_for_recommendation` folded or scoped-out; `test_git_ops` + `mission_branch_context` tests green.
**Prompt**: `/tasks/WP04-resolve-primary-branch-consolidation.md`
**Requirement Refs**: FR-007

### Included Subtasks

- [x] T013 Red-first: pin canonical `resolve_primary_branch` behavior + the recommendation no-feature-bias behavior
- [x] T014 Resolve `cli/commands/agent/tasks_shared.py` shim (keep-as-explicit-compat or remove) + update `tasks.py.__all__` + `test_tasks_compat_surface`
- [x] T015 Fold `_resolve_primary_branch_for_recommendation` (`mission_branch_context.py:197`) into canonical via `bias` param, OR scope out with a recorded rationale comment
- [x] T016 Green: `test_git_ops`, `test_tasks_compat_surface`, `mission_branch_context` tests + `ruff`/`mypy --strict`

### Dependencies
- None.

### Risks & Mitigations
- Compat contract (`tasks.py.__all__` + `test_tasks_compat_surface`) must move in lockstep; preserve the deliberate no-feature-bias behavior of the recommendation path.

---

## Work Package WP05: Internal helper renames (merge + Sense-D) (Priority: P2)

**Goal**: Align genuinely internal helper names to canonical operations, updating the full blast radius. `is_primary_artifact_kind` EXCLUDED (public).
**Independent Test**: `merge_lane_to_mission`/`merge_mission_to_target`/`_primary_ref_for` renamed; all callers (incl. `orchestrator_api`) + ~13 test importers + `write_candidate_classification.yaml` arch fixture + the 2 `_primary_ref_for` pinning tests move together; surface-audit + full suite green.
**Prompt**: `/tasks/WP05-internal-helper-renames.md`
**Requirement Refs**: FR-008, FR-003 (lanes/merge.py docstrings)

### Included Subtasks

- [x] T017 Rename `merge_lane_to_mission`→consolidate-sense + `merge_mission_to_target`→integrate-sense in `lanes/merge.py` (+ clarify their docstrings) and update `orchestrator_api/commands.py` callers + ~13 test importers + `surface_resolution_audit/write_candidate_classification.yaml`
- [x] T018 Rename `_primary_ref_for` (`implement_cores.py`) + update `implement.py` + `test_precondition_ref_unification.py` + `test_partition_authority_characterization.py`
- [x] T019 (optional) Rename `_resolve_primary_target_branch` (`commit_router.py:553`) internal Sense-B/D helper
- [x] T020 Green: full suite + surface-audit gate + `ruff`/`mypy --strict`

### Dependencies
- Depends on WP04 (same code review area — sequence to avoid churn).

### Risks & Mitigations
- Helpers are broadly imported (not "internal-only") → every caller + arch fixture must move in the same change or the surface-audit gate reds.

---

## Work Package WP06: Enforcement disclosure + verification wrap (Priority: P3)

**Goal**: Verify occurrence-map diff-compliance + all SCs; honestly disclose the enforcement model; OPTIONALLY extend the terminology guard with non-Sense-C alias bans if a clean grep confirms zero legitimate residual.
**Independent Test**: SC-001..SC-006 confirmed; `occurrence_map.yaml` diff-compliance passes; all gates green; enforcement model stated (FR-011); any alias-ban added only after a zero-residual grep, else deferred to Track 2 with rationale.
**Prompt**: `/tasks/WP06-enforcement-and-verification.md`
**Requirement Refs**: FR-009, FR-010, FR-011, NFR-001, NFR-002, NFR-003, NFR-004

### Included Subtasks

- [ ] T021 Verify exempt-token invariance (SC-002 grep) + occurrence_map per-category diff-compliance
- [ ] T022 Run all gates (anti-sprawl `--strict`, description-length, relative-link, terminology guard proven-executed, ruff, mypy --strict); confirm exempt-surface pins green
- [x] T023 (optional) Extend `test_no_legacy_terminology.py` with `"primary target"`/`"primary ref"` bans ONLY if `git grep` shows zero legitimate residual in scanned dirs; else document deferral to Track 2
- [x] T024 Confirm FR-011 enforcement disclosure present; run `quickstart.md` SC walkthrough

### Dependencies
- Depends on WP01, WP02, WP03, WP04, WP05.

### Risks & Mitigations
- A repo-wide alias ban reds if any legitimate/Sense-C residual remains → gate T023 behind a zero-residual grep; default to deferral.

---

## Dependency & Execution Summary

- **Sequence**: (WP01, WP04 start in parallel) → WP02 & WP03 after WP01; WP05 after WP04 → WP06 last.
- **Parallelization**: WP01∥WP04; WP02∥WP03 (disjoint files); WP05 after WP04.
- **MVP Scope**: WP01 + WP02 (the vocabulary deliverable). WP03–WP06 are hygiene + safe-code + verification.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP02, WP05 |
| FR-004 | WP01 |
| FR-005 | WP03 |
| FR-006 | WP03 |
| FR-007 | WP04 |
| FR-008 | WP05 |
| FR-009 | WP06 |
| FR-010 | WP06 |
| FR-011 | WP02, WP06 |
| NFR-001 | WP06 |
| NFR-002 | WP04, WP06 |
| NFR-003 | WP06 |
| NFR-004 | WP06 |
| C-001..C-006 | all (occurrence_map-enforced) |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001–T004 | Glossary sense entries | WP01 | P1 | Partial |
| T005–T009 | Prose/help/docstring sweep | WP02 | P1 | Partial |
| T010–T012 | Glossary-infra cleanup | WP03 | P2 | No |
| T013–T016 | resolve_primary_branch consolidation | WP04 | P2 | No |
| T017–T020 | Internal helper renames | WP05 | P2 | No |
| T021–T024 | Enforcement + verification | WP06 | P3 | No |
