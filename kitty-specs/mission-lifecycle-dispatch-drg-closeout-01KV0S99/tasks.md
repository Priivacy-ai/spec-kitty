# Tasks — Mission lifecycle, dispatch & DRG closeout (01KV0S99)

**Branch (planning = merge target):** `feat/mission-lifecycle-dispatch-drg-closeout` (PR-bound onto `upstream/main`).
**Source of truth:** spec.md (FR/NFR/C/SC), plan.md (IC-01..IC-10), research.md (decisions + review corrections), data-model.md, contracts/, quickstart.md.

5 work packages across 3 independent lanes. ATDD throughout (failing acceptance test first — NFR-005). Closure verdicts (issue-matrix terminal rows) are set at the mission accept/merge gate, not owned by any single WP.

## Lanes / dependency graph

- **Lane A (post-mission lifecycle):** WP01 → WP02
- **Lane B (dispatch unification):** WP03 → WP04
- **Lane C (DRG curation):** WP05 (independent)

WP01, WP03, WP05 have no dependencies (parallel start). WP02 depends on WP01; WP04 depends on WP03.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | ATDD: failing tests for MissionReopened/FollowUpRecorded emit + reducer-skip + re-open classification | WP01 | | [D] |
| T002 | Register MissionReopened/FollowUpRecorded in LIFECYCLE_EVENT_TYPES + __all__; emit helpers + dedup | WP01 | | [D] |
| T003 | derive_mission_lifecycle/_classify_state: honor MissionReopened → `reopened` surface_state (the FR-002 crux) | WP01 | | [D] |
| T004 | Keep new types off the SaaS strict-validation path (local-only); confirm reducer-skip round-trip | WP01 | | [D] |
| T005 | ATDD: failing tests for `mission reopen` / `mission follow-up` (incl. fail-closed + idempotency) | WP02 | | [D] |
| T006 | `mission reopen` subcommand: clear merged_*, append event, fail-closed predicate | WP02 | | [D] |
| T007 | `mission follow-up` subcommand: idempotent dedup on (mission_id, commit_sha|pr_number) | WP02 | | [D] |
| T008 | Handle resolver (mission_id/mid8/slug → feature_dir; ambiguous → MISSION_AMBIGUOUS_SELECTOR) | WP02 | | [D] |
| T009 | Render post_mission_events in the lifecycle/history view (views.py) | WP02 | | [D] |
| T010 | #1802 closure: confirm FR-001/002 scope or split residual to a child; ready issue-matrix row | WP02 | | [D] |
| T011 | ATDD: dispatch parity tests (do/ask/advise/dispatch byte/contract-identical Op records + envelopes) | WP03 | | [D] |
| T012 | Extract shared `_dispatch_impl` (unify duplicated helpers across do_cmd.py + advise.py) | WP03 | | [D] |
| T013 | Add canonical `spec-kitty dispatch` command; rewire do/ask/advise as thin aliases (atomic, C-002) | WP03 | | [D] |
| T014 | Add `dispatch` to invocation/modes.py `_ENTRY_COMMAND_MODE`; register in __init__.py | WP03 | | [D] |
| T015 | Add `dispatch` to SOURCE skill `spec-kitty.advise/SKILL.md`; refresh command-skills manifest | WP04 | | [D] |
| T016 | Update skill-routing prose naming the trio to include `dispatch` | WP04 | | [D] |
| T017 | #1810/#1804 closure: verify epic substantially complete; ready issue-matrix rows | WP04 | | [D] |
| T018 | ATDD: orphan-count regression test (pins reduced count; freshness/byte-identical stay green) | WP05 | | [D] |
| T019 | Repaint java-conventions java-implementer→java-jenny; sweep same-class stale refs (pattern-match AND target-absent) | WP05 | | [D] |
| T020 | Orphan triage: wire real inbound edges where a natural referent exists | WP05 | | [D] |
| T021 | Document residual orphans (per-orphan rationale) + file curation follow-up if non-empty | WP05 | | [D] |
| T022 | Regenerate graph.yaml deterministically (`doctrine regenerate-graph`); confirm `--check` green | WP05 | | [D] |
| T023 | #1863 closure: ready issue-matrix row | WP05 | | [D] |
| T024 | Baseline: status suite green; enumerate the 17 adjacent mypy --strict errors | WP06 | | [D] |
| T025 | Clear emit.py mypy --strict errors (type-only, behavior-preserving) | WP06 | | [D] |
| T026 | Clear aggregate.py + status/__init__.py + progress.py mypy --strict errors | WP06 | | [D] |
| T027 | Verify `mypy --strict src/specify_cli/status/` exits 0 (with WP01/WP02); status suite green (SC-6) | WP06 | | [D] |

---

## WP01 — Lifecycle events + re-open-aware classification (Lane A foundation)

- **Goal:** Add `MissionReopened` and `FollowUpRecorded` lifecycle events and teach `derive_mission_lifecycle` to honor `MissionReopened` as the authority that makes a re-opened mission actionable.
- **Priority:** High (lane-A foundation; blocks WP02). **Independent test:** emit a MissionReopened on a fixture merged mission → `derive_mission_lifecycle` reports `reopened`/actionable; emit FollowUpRecorded twice with same ref → one event.
- **Dependencies:** none.
- **Requirements:** FR-001, FR-002, NFR-002, NFR-004, NFR-005.
- **Subtasks:** T001, T002, T003, T004.
- **Prompt:** [tasks/WP01-lifecycle-events-classification.md](tasks/WP01-lifecycle-events-classification.md)
- **Risks:** the classification change (T003) is the FR-002 crux — clearing merged_* alone is a no-op. Keep events reducer-skipped + off the SaaS strict path.

## WP02 — Mission reopen/follow-up commands + history view + #1802 closure (Lane A)

- **Goal:** Ship `spec-kitty mission reopen` and `mission follow-up` over the WP01 events, render them in history, and bring #1802 to honest closure.
- **Priority:** High. **Independent test:** quickstart A scenarios 1–5.
- **Dependencies:** WP01.
- **Requirements:** FR-001, FR-002, FR-003, NFR-002, NFR-004.
- **Subtasks:** T005, T006, T007, T008, T009, T010.
- **Prompt:** [tasks/WP02-mission-lifecycle-commands.md](tasks/WP02-mission-lifecycle-commands.md)
- **Risks:** re-open must NOT cascade WP lanes (actionability comes from WP01's classifier); fail-closed predicate per contract; do not edit lifecycle.py's classifier (WP01 owns it) — only views.py here.

## WP03 — Unify dispatch: canonical command + aliases + parity (Lane B foundation)

- **Goal:** Add canonical `spec-kitty dispatch` over the existing `invocation/` mechanism; keep do/ask/advise as byte-identical first-class aliases; pin parity.
- **Priority:** High (lane-B foundation; blocks WP04). **Independent test:** quickstart B scenarios 6–8.
- **Dependencies:** none.
- **Requirements:** FR-004, FR-005, NFR-001, NFR-002.
- **Subtasks:** T011, T012, T013, T014.
- **Prompt:** [tasks/WP03-unify-dispatch.md](tasks/WP03-unify-dispatch.md)
- **Risks:** C-002 — atomic; never a commit where the trio is broken. Preserve each verb's exact arg shape + mode.

## WP04 — Dispatch propagation to canonical skill + #1810/#1804 closure (Lane B)

- **Goal:** Propagate `dispatch` to the single canonical command-skill + manifest + routing prose; close #1810 and epic #1804.
- **Priority:** Medium. **Independent test:** quickstart B scenario 9.
- **Dependencies:** WP03.
- **Requirements:** FR-006, FR-007, NFR-002, C-004.
- **Subtasks:** T015, T016, T017.
- **Prompt:** [tasks/WP04-dispatch-propagation-closure.md](tasks/WP04-dispatch-propagation-closure.md)
- **Risks:** ONE generated skill (`spec-kitty.advise`), not 19-way; never hand-edit agent copies.

## WP05 — DRG curation: stale-ref repair + orphan triage + deterministic regen + #1863 closure (Lane C)

- **Goal:** Repair the java-implementer stale ref (+ same-class), triage orphans (wire-or-document, never bulk-delete), regenerate deterministically, pin the reduced count, close #1863.
- **Priority:** Medium. **Independent test:** quickstart C scenarios 10–12.
- **Dependencies:** none.
- **Requirements:** FR-008, FR-009, NFR-002, NFR-003, C-003.
- **Subtasks:** T018, T019, T020, T021, T022, T023.
- **Prompt:** [tasks/WP05-drg-curation.md](tasks/WP05-drg-curation.md)
- **Risks:** content-destruction — NO bulk-delete of valid unreferenced doctrine; prune only genuinely-retired, individually justified. graph emit already deterministic — pin, don't re-architect.

## WP06 — Type-safety boyscout: status/ package mypy --strict clean (cross-cutting, opportunistic)

- **Goal:** clear the 17 adjacent `mypy --strict` errors on un-owned `status/` files so
  `mypy --strict src/specify_cli/status/` exits 0 (SC-6), behavior-preserving.
- **Priority:** Low (opportunistic). **Independent test:** `mypy --strict src/specify_cli/status/` exits 0; status suite green.
- **Dependencies:** none (no file overlap with WP01/WP02 — different files in the same package).
- **Requirements:** NFR-002, SC-6.
- **Subtasks:** T024, T025, T026, T027.
- **Prompt:** [tasks/WP06-status-typesafety-boyscout.md](tasks/WP06-status-typesafety-boyscout.md)
- **Risks:** `emit.py` is critical-path — type-only fixes, no logic change; do not expand beyond `status/`.

---

## MVP scope

WP01 + WP03 + WP05 (the three lane foundations) can start in parallel immediately. WP01 is the highest-leverage MVP slice (unblocks the #1802 surface). Lane C (WP05) is the lowest-risk independent closure.
