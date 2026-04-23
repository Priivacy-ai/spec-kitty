# Tasks: Phase 4 Closeout — Host-Surface Breadth and Trail Follow-On

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Baseline commit**: `eb32cf0a` on `origin/main` (2026-04-23)

## Branch Contract

- Current branch at tasks start: `main`
- Planning / base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: `true`

## Execution Summary

**Tranche A** (host-surface breadth, 5 WPs) ships first. **Tranche B** (trail follow-on, 4 WPs) begins only after Tranche A is approved.

Smallest next chunk to build first: **WP01** (inventory matrix), followed immediately by **WP02** (dashboard wording fix) which can run in parallel with WP03 and WP04.

---

## Subtask Index

Reference table only — status is tracked via per-WP checkboxes below.

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Scaffold host-surface inventory matrix file | WP01 |  | [D] |
| T002 | Audit slash-command surfaces (13) for advise/ask/do parity | WP01 | [D] |
| T003 | Audit Agent Skills surfaces (Codex, Vibe) | WP01 | [D] |
| T004 | Populate inventory rows + parity_status + notes | WP01 |  | [D] |
| T005 | Replace user-visible `Feature` strings in `dashboard/templates/index.html` | WP02 |  | [D] |
| T006 | Replace user-visible `Feature` strings in `dashboard/static/dashboard/dashboard.js` | WP02 |  | [D] |
| T007 | Replace `"no feature context"` in `dashboard/diagnostics.py` | WP02 |  | [D] |
| T008 | Write wording + backend-preservation snapshot test | WP02 |  | [D] |
| T009 | Live dashboard visual verification | WP02 |  | [D] |
| T010 | Audit + update `README.md` governance layer subsection | WP03 |  | [D] |
| T011 | Terminology consistency pass on `.agents/skills/spec-kitty.advise/SKILL.md` | WP03 | [D] |
| T012 | Terminology consistency pass on `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` | WP03 | [D] |
| T013 | Snapshot test asserting README governance subsection structure | WP03 |  | [D] |
| T014 | Link-target regression test for canonical skill-pack pointers | WP03 |  | [D] |
| T015 | Establish the parity-file pattern (inline vs pointer) for each non-parity surface | WP04 |  | [D] |
| T016 | Ship parity content for surface group 1 (copilot, gemini, cursor, qwen) | WP04 | [D] |
| T017 | Ship parity content for surface group 2 (opencode, windsurf, kilocode) | WP04 | [D] |
| T018 | Ship parity content for surface group 3 (auggie, roo, q, kiro, agent) | WP04 | [D] |
| T019 | Update inventory matrix to reflect post-rollout parity status | WP04 |  | [D] |
| T020 | Promote inventory to `docs/host-surface-parity.md` with preamble | WP05 |  | [D] |
| T021 | Add link from `docs/trail-model.md` to the promoted matrix | WP05 |  | [D] |
| T022 | Verify link from README governance section to promoted matrix | WP05 |  | [D] |
| T023 | Add parity-coverage test `tests/specify_cli/docs/test_host_surface_inventory.py` | WP05 |  | [D] |
| T024 | Mark `#496` as delivered in the tracker-hygiene checklist for WP09 | WP05 |  | [D] |
| T025 | Wire merge-ready signal: all Tranche A tests green | WP05 |  | [D] |
| T026 | Create `modes.py` with `ModeOfWork` + `derive_mode()` + unit tests | WP06 |  | [D] |
| T027 | Extend `InvocationRecord` with optional `mode_of_work`; executor threads kwarg | WP06 |  | [D] |
| T028 | Add `append_correlation_link()` + shared `normalise_ref()` to `writer.py` | WP06 |  | [D] |
| T029 | Add `InvalidModeForEvidenceError`; enforce in `complete_invocation` | WP06 |  | [D] |
| T030 | CLI wiring for advise/ask/do/complete (`advise.py`, `do_cmd.py`) — mode + correlation flags | WP06 |  | [D] |
| T031 | CLI wiring for query + mission-step paths (`profiles_cmd.py`, `invocations_cmd.py`, `next_cmd.py`) | WP06 |  | [D] |
| T032 | Integration tests: e2e + correlation + enforcement + backwards compat | WP06 |  | [D] |
| T033 | Create `projection_policy.py` with `EventKind`, `ProjectionRule`, `POLICY_TABLE`, `resolve_projection()` | WP07 |  | [D] |
| T034 | Modify `_propagate_one` to consult `resolve_projection`; gate envelope field inclusion | WP07 |  | [D] |
| T035 | Unit tests for all 16 policy rows + null-mode fallback | WP07 |  | [D] |
| T036 | Integration tests: propagator under mocked client; each (mode, event) pair | WP07 |  | [D] |
| T037 | NFR-007 / SC-008 assertion: propagation-errors.jsonl empty under sync-disabled | WP07 |  | [D] |
| T038 | Golden-path regression: existing task_execution / mission_step timeline behaviour preserved | WP07 |  | [D] |
| T039 | Add "Mode of Work (runtime-enforced)" subsection to `docs/trail-model.md` | WP08 |  |
| T040 | Add "Correlation Links" subsection to `docs/trail-model.md` | WP08 |  |
| T041 | Add "SaaS Read-Model Policy" subsection + full table to `docs/trail-model.md` | WP08 |  |
| T042 | Add "Tier 2 SaaS Projection — Deferred" subsection to `docs/trail-model.md` | WP08 |  |
| T043 | Update `CHANGELOG.md` unreleased section with Tranche A + Tranche B summaries + migration note | WP08 |  |
| T044 | Add doc-presence test `tests/specify_cli/docs/test_trail_model_doc.py` | WP08 |  |
| T045 | Prepare `#496` close comment + close on Tranche A delivery | WP09 |  |
| T046 | Prepare `#701` close comment + close on mission merge | WP09 |  |
| T047 | Update `#466` (Phase 4 tracker) — Phase 4 follow-on shipped | WP09 |  |
| T048 | Cross-link `#534` to `#499` / `#759` as Phase 5 glossary-foundation unblocker | WP09 |  |
| T049 | Verify `#461` umbrella roadmap left open | WP09 |  |
| T050 | Retitle `#496` to reflect delivered scope if needed | WP09 |  |
| T051 | Document completed hygiene actions in the PR description | WP09 |  |

Totals: **9 work packages, 51 subtasks.** Average size ~5.7 subtasks / WP. No WP exceeds 7 subtasks.

---

## Tranche A — Host-Surface Breadth (#496)

### WP01 — Host-Surface Inventory Matrix

**Goal**: Produce the authoritative parity matrix across all 15 supported host surfaces.

**Priority**: Tranche A foundation.

**Independent test**: Running the WP01 deliverable produces a complete matrix file; every `AGENT_DIRS` key has exactly one row.

**Included subtasks**:

- [x] T001 Scaffold host-surface inventory matrix file
- [x] T002 Audit slash-command surfaces (13) for advise/ask/do parity
- [x] T003 Audit Agent Skills surfaces (Codex, Vibe)
- [x] T004 Populate inventory rows + parity_status + notes

**Dependencies**: none.
**Execution mode**: `planning_artifact`.
**Owned files**: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md`.
**Estimated prompt size**: ~300 lines.
**Prompt**: `tasks/WP01-host-surface-inventory.md`.

### WP02 — Dashboard User-Visible Wording Fix

**Goal**: Replace user-visible `Feature` strings in the three dashboard files with `Mission Run` vocabulary. Backend identifiers stay unchanged per FR-004.

**Priority**: Tranche A — the smallest code-touching chunk.

**Independent test**: Open the dashboard in a browser; no user-visible `Feature` string remains on the mission selector, current-mission header, breadcrumbs, or empty state.

**Included subtasks**:

- [x] T005 Replace user-visible `Feature` strings in `dashboard/templates/index.html`
- [x] T006 Replace user-visible `Feature` strings in `dashboard/static/dashboard/dashboard.js`
- [x] T007 Replace `"no feature context"` in `dashboard/diagnostics.py`
- [x] T008 Write wording + backend-preservation snapshot test
- [x] T009 Live dashboard visual verification

**Dependencies**: WP01 (inventory captures this surface).
**Execution mode**: `code_change`.
**Owned files**: `src/specify_cli/dashboard/templates/index.html`, `src/specify_cli/dashboard/static/dashboard/dashboard.js`, `src/specify_cli/dashboard/diagnostics.py`, `tests/specify_cli/dashboard/test_dashboard_wording.py`.
**Estimated prompt size**: ~400 lines.
**Prompt**: `tasks/WP02-dashboard-wording-fix.md`.

### WP03 — README + Canonical Skills Terminology Sweep

**Goal**: Add a `Governance layer` subsection to `README.md`; audit + correct vocabulary in the two canonical skill packs (`.agents/skills/spec-kitty.advise/SKILL.md` and `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`) for consistency with the Phase 4 runtime vocabulary and with WP02's Mission Run rename.

**Priority**: Tranche A — parallel with WP02 and WP04.

**Independent test**: README renders a Governance layer subsection with links to `docs/trail-model.md` and `docs/host-surface-parity.md`; no stale `Feature` terminology in either canonical skill pack where the concept is a Mission Run.

**Included subtasks**:

- [x] T010 Audit + update `README.md` governance layer subsection
- [x] T011 Terminology consistency pass on `.agents/skills/spec-kitty.advise/SKILL.md`
- [x] T012 Terminology consistency pass on `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`
- [x] T013 Snapshot test asserting README governance subsection structure
- [x] T014 Link-target regression test for canonical skill-pack pointers

**Dependencies**: WP01 (inventory identifies terminology gaps).
**Execution mode**: `code_change`.
**Owned files**: `README.md`, `.agents/skills/spec-kitty.advise/SKILL.md`, `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`, `tests/specify_cli/docs/test_readme_governance.py`.
**Estimated prompt size**: ~350 lines.
**Prompt**: `tasks/WP03-readme-and-canonical-skills.md`.

### WP04 — Skill-Pack Parity Rollout to Remaining Agent Surfaces

**Goal**: Bring the 12 non-canonical host surfaces (all slash-command agents except `claude` which is covered by the `runtime-next` doctrine skill) to parity with the advise/ask/do governance-injection contract. Either inline content or a pointer per-surface, documented in the inventory.

**Priority**: Tranche A — parallel with WP02 and WP03.

**Independent test**: Every non-canonical surface contains either inline parity content or an explicit pointer file; the inventory matrix shows `parity_status=at_parity` for all 15 surfaces after WP04 closes.

**Included subtasks**:

- [x] T015 Establish the parity-file pattern (inline vs pointer) for each non-parity surface
- [x] T016 Ship parity content for surface group 1 (copilot, gemini, cursor, qwen)
- [x] T017 Ship parity content for surface group 2 (opencode, windsurf, kilocode)
- [x] T018 Ship parity content for surface group 3 (auggie, roo, q, kiro, agent)
- [x] T019 Update inventory matrix to reflect post-rollout parity status

**Dependencies**: WP01 (inventory scope drives the rollout).
**Execution mode**: `code_change`.
**Owned files**: `.github/prompts/spec-kitty-standalone.md`, `.gemini/commands/spec-kitty-standalone.md`, `.cursor/commands/spec-kitty-standalone.md`, `.qwen/commands/spec-kitty-standalone.md`, `.opencode/command/spec-kitty-standalone.md`, `.windsurf/workflows/spec-kitty-standalone.md`, `.kilocode/workflows/spec-kitty-standalone.md`, `.augment/commands/spec-kitty-standalone.md`, `.roo/commands/spec-kitty-standalone.md`, `.amazonq/prompts/spec-kitty-standalone.md`, `.kiro/prompts/spec-kitty-standalone.md`, `.agent/workflows/spec-kitty-standalone.md`.
**Estimated prompt size**: ~450 lines.
**Prompt**: `tasks/WP04-skill-pack-parity-rollout.md`.

### WP05 — Inventory Promotion + Tranche A Closeout

**Goal**: Promote the living matrix to `docs/host-surface-parity.md`, add links from `docs/trail-model.md` and README, ship the coverage test, and mark Tranche A ready for merge.

**Priority**: Tranche A closeout — must run after WP02, WP03, WP04 all merge.

**Independent test**: `docs/host-surface-parity.md` exists with every `AGENT_DIRS` surface listed; `tests/specify_cli/docs/test_host_surface_inventory.py` passes green; the promoted doc is linked from `docs/trail-model.md` and README.

**Included subtasks**:

- [x] T020 Promote inventory to `docs/host-surface-parity.md` with preamble
- [x] T021 Add link from `docs/trail-model.md` to the promoted matrix
- [x] T022 Verify link from README governance section to promoted matrix
- [x] T023 Add parity-coverage test `tests/specify_cli/docs/test_host_surface_inventory.py`
- [x] T024 Mark `#496` as delivered in the tracker-hygiene checklist for WP09
- [x] T025 Wire merge-ready signal: all Tranche A tests green

**Dependencies**: WP02, WP03, WP04.
**Execution mode**: `code_change`.
**Owned files**: `docs/host-surface-parity.md`, `tests/specify_cli/docs/test_host_surface_inventory.py`.
**Estimated prompt size**: ~400 lines.
**Prompt**: `tasks/WP05-inventory-promotion-tranche-a-closeout.md`.

---

## Tranche B — Trail Follow-On (#701)

### WP06 — Trail Enrichment: Mode Derivation + Correlation + Enforcement

**Goal**: Implement three coupled changes inside the invocation runtime: (1) runtime derivation of `mode_of_work` from the CLI entry command, recorded on the `started` event; (2) append-only correlation events (`artifact_link`, `commit_link`) on the invocation JSONL, driven by new flags on `profile-invocation complete`; (3) mode-aware enforcement that rejects Tier 2 evidence promotion for `advisory` / `query` invocations with a typed error.

**Priority**: Tranche B foundation.

**Independent test**: End-to-end — open each of advise/ask/do, verify the `started` event carries the expected `mode_of_work`; close a task_execution invocation with `--artifact a --artifact b --commit sha`, verify the two correlation events + one commit_link append in order; attempt `--evidence` on an advisory invocation and verify `InvalidModeForEvidenceError` is raised before any append. All local-first invariants preserved.

**Included subtasks**:

- [x] T026 Create `modes.py` with `ModeOfWork` + `derive_mode()` + unit tests
- [x] T027 Extend `InvocationRecord` with optional `mode_of_work`; executor threads kwarg
- [x] T028 Add `append_correlation_link()` + shared `normalise_ref()` to `writer.py`
- [x] T029 Add `InvalidModeForEvidenceError`; enforce in `complete_invocation`
- [x] T030 CLI wiring for advise/ask/do/complete (`advise.py`, `do_cmd.py`) — mode + correlation flags
- [x] T031 CLI wiring for query + mission-step paths (`profiles_cmd.py`, `invocations_cmd.py`, `next_cmd.py`)
- [x] T032 Integration tests: e2e + correlation + enforcement + backwards compat

**Dependencies**: WP05 (Tranche A must close before Tranche B begins).
**Execution mode**: `code_change`.
**Owned files**: `src/specify_cli/invocation/modes.py`, `src/specify_cli/invocation/record.py`, `src/specify_cli/invocation/writer.py`, `src/specify_cli/invocation/executor.py`, `src/specify_cli/invocation/errors.py`, `src/specify_cli/cli/commands/advise.py`, `src/specify_cli/cli/commands/do_cmd.py`, `src/specify_cli/cli/commands/next_cmd.py`, `src/specify_cli/cli/commands/profiles_cmd.py`, `src/specify_cli/cli/commands/invocations_cmd.py`, `tests/specify_cli/invocation/test_modes.py`, `tests/specify_cli/invocation/test_correlation.py`, `tests/specify_cli/invocation/test_invocation_e2e.py`.
**Estimated prompt size**: ~650 lines.
**Prompt**: `tasks/WP06-trail-enrichment.md`.

### WP07 — SaaS Read-Model Policy

**Goal**: Implement the typed `projection_policy.py` module + `POLICY_TABLE` + `resolve_projection()`; wire `_propagate_one` through the policy lookup; ensure the local-first invariant is preserved and existing dashboard behaviour for `task_execution` / `mission_step` events is unchanged.

**Priority**: Tranche B.

**Independent test**: Unit tests cover all 16 `(mode, event)` rows; integration tests exercise `_propagate_one` under each pair with a mocked connected client; golden-path tests assert `task_execution/started` and `mission_step/completed` behaviour is unchanged from 3.2.0a5.

**Included subtasks**:

- [x] T033 Create `projection_policy.py` with `EventKind`, `ProjectionRule`, `POLICY_TABLE`, `resolve_projection()`
- [x] T034 Modify `_propagate_one` to consult `resolve_projection`; gate envelope field inclusion
- [x] T035 Unit tests for all 16 policy rows + null-mode fallback
- [x] T036 Integration tests: propagator under mocked client; each (mode, event) pair
- [x] T037 NFR-007 / SC-008 assertion: propagation-errors.jsonl empty under sync-disabled
- [x] T038 Golden-path regression: existing task_execution / mission_step timeline behaviour preserved

**Dependencies**: WP06.
**Execution mode**: `code_change`.
**Owned files**: `src/specify_cli/invocation/projection_policy.py`, `src/specify_cli/invocation/propagator.py`, `tests/specify_cli/invocation/test_projection_policy.py`, `tests/specify_cli/invocation/test_propagator_policy.py`.
**Estimated prompt size**: ~500 lines.
**Prompt**: `tasks/WP07-saas-read-model-policy.md`.

### WP08 — Post-Tranche-B Operator Docs + CHANGELOG

**Goal**: Add four new subsections to `docs/trail-model.md` (Mode of Work, Correlation Links, SaaS Read-Model Policy table, Tier 2 SaaS Projection Deferral) and the Tranche A + Tranche B unreleased CHANGELOG entry with migration notes.

**Priority**: Tranche B.

**Independent test**: Doc-presence test asserts every new subsection heading is present in `docs/trail-model.md`; CHANGELOG unreleased section includes both tranches + migration note.

**Included subtasks**:

- [ ] T039 Add "Mode of Work (runtime-enforced)" subsection to `docs/trail-model.md`
- [ ] T040 Add "Correlation Links" subsection to `docs/trail-model.md`
- [ ] T041 Add "SaaS Read-Model Policy" subsection + full table to `docs/trail-model.md`
- [ ] T042 Add "Tier 2 SaaS Projection — Deferred" subsection to `docs/trail-model.md`
- [ ] T043 Update `CHANGELOG.md` unreleased section with Tranche A + Tranche B summaries + migration note
- [ ] T044 Add doc-presence test `tests/specify_cli/docs/test_trail_model_doc.py`

**Dependencies**: WP06, WP07.
**Execution mode**: `code_change`.
**Owned files**: `docs/trail-model.md`, `CHANGELOG.md`, `tests/specify_cli/docs/test_trail_model_doc.py`.
**Estimated prompt size**: ~400 lines.
**Prompt**: `tasks/WP08-post-tranche-b-docs.md`.

### WP09 — Tracker Hygiene

**Goal**: Close and update GitHub issues to reflect delivered scope. Close `#496` on Tranche A merge, close `#701` on mission merge, update `#466` (Phase 4 tracker), cross-link `#534` to its Phase 5 unblocker, leave `#461` open.

**Priority**: Tranche B — final WP before mission close.

**Independent test**: `gh issue view` confirms the expected state for each of `#496`, `#701`, `#466`, `#534`, `#461` after the closing agent runs the hygiene checklist.

**Included subtasks**:

- [ ] T045 Prepare `#496` close comment + close on Tranche A delivery
- [ ] T046 Prepare `#701` close comment + close on mission merge
- [ ] T047 Update `#466` (Phase 4 tracker) — Phase 4 follow-on shipped
- [ ] T048 Cross-link `#534` to `#499` / `#759` as Phase 5 glossary-foundation unblocker
- [ ] T049 Verify `#461` umbrella roadmap left open
- [ ] T050 Retitle `#496` to reflect delivered scope if needed
- [ ] T051 Document completed hygiene actions in the PR description

**Dependencies**: WP08.
**Execution mode**: `planning_artifact` (GitHub tracker work only — no code changes).
**Owned files**: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/tracker-hygiene.md` (checklist artifact recording what was done).
**Estimated prompt size**: ~300 lines.
**Prompt**: `tasks/WP09-tracker-hygiene.md`.

---

## Parallelization Highlights

```
Tranche A:
  WP01 (inventory)
    ├── WP02 dashboard wording   ─┐
    ├── WP03 README + skills     ─┤─→ WP05 promotion
    └── WP04 skill-pack rollout  ─┘
        (WP02, WP03, WP04 may all run in parallel after WP01 merges)

Tranche B:
  WP05 (Tranche A closeout)
    └── WP06 trail enrichment
        └── WP07 SaaS policy
            └── WP08 docs + CHANGELOG
                └── WP09 tracker hygiene
```

Three Tranche A WPs (WP02, WP03, WP04) can run simultaneously once WP01 lands, giving meaningful parallelism. Tranche B is strictly sequential (four WPs) because each builds on the previous: policy needs mode + events; docs describe both; hygiene closes the package.

## Dependencies Summary

| WP | Depends on |
|----|------------|
| WP01 | (none) |
| WP02 | WP01 |
| WP03 | WP01 |
| WP04 | WP01 |
| WP05 | WP02, WP03, WP04 |
| WP06 | WP05 |
| WP07 | WP06 |
| WP08 | WP06, WP07 |
| WP09 | WP08 |

## MVP Scope Recommendation

The mission is a closeout, not an MVP build. However, if scope must be reduced, Tranche A alone (**WP01 → WP05**) is shippable on its own as the `#496` closure; Tranche B can follow in a subsequent release. Do not cut mid-tranche.

## Requirement Coverage

- FR-001: WP01, WP05
- FR-002: WP04
- FR-003: WP02
- FR-004: WP02
- FR-005: WP03
- FR-006: WP04
- FR-007: WP06
- FR-008: WP06
- FR-009: WP06
- FR-010: WP07
- FR-011: WP08
- FR-012: WP06, WP07
- FR-013: WP08
- FR-014: WP09
