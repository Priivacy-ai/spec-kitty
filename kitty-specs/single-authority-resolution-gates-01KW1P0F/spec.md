# Single-Authority Resolution Gates

**Mission ID:** 01KW1P0FRYK89H5TK5QK8148X9 · **Type:** software-dev · **Target branch:** `design/infra-logic-separation-2173`
**Epic:** #2173 Phase 1 (sub of #1619) · **Binding design:** ADR `architecture/3.x/adr/2026-06-26-1-single-authority-seam-and-call-site-gate.md` + `docs/engineering_notes/2173-infra-logic-separation/00-SYNTHESIS.md`

## Overview & Context

Mission-artifact paths (task-index and status files, primary mission dirs) are resolved through seams that *several callers bypass*. Two consequences are live P0 blockers, and a third is a latent regression hazard:

- **The write leg bypasses the kind-aware authority (#2154).** `mark_status`'s *write* composes the coordination-worktree dir via the kind-**blind** resolver, while its *commit* and `move_task`'s *validation* correctly use the kind-**aware** authority targeting the primary surface. Result: every work package blocks on phantom "unchecked subtasks."
- **A blanket commit guard conflicts with the surface partition (#2155).** `safe_commit` refuses any `.worktrees/` path staged from the repo root, firing on legitimate coordination-owned status writes — so the status event log stays uncommitted on every transition.
- **The handle-canonicalization boundary has no regression guard (#2164 residual).** The read-leg fix shipped (#2161, a pre-condition), but the `primary_feature_dir_for_mission` primitive is topology-blind-by-design and **auto-blessed** by every existing gate; nothing checks whether the handle reaching it was canonicalized. Only 2 of ~34 call sites canonicalize today. A future cloned write seam re-introduces the divergence #2164 fixed, silently.

The unifying defect (ADR 2026-06-26-1): crossing a resolution boundary is a *convention every caller must remember*, and the conventions diverge. The fix is **single-authority-at-the-seam + an AST call-site gate** that makes the omission a CI failure — generalizing the proven in-repo pattern (`test_protection_resolver_call_sites.py` / `test_single_mission_surface_resolver.py`).

This mission is **Phase 1**: route the bypassing write legs through the *existing* authority, and add the gates. It explicitly does **not** introduce the Phase 2 `MissionResolver` DI port.

## User Scenarios & Testing

**Primary actor:** an engineer or agent running the `implement → review` loop.

1. **Happy path (unblocked loop):** An implementer marks subtasks done (`mark_status`), then advances the WP (`move_task --to for_review`). The status write and its validation read the *same* surface → the WP advances. *(Today this blocks on "unchecked subtasks.")*
2. **Status commit under coordination topology:** A status transition is committed. The coordination-owned status write is staged and committed without the repo-root guard refusing it. *(Today `safe_commit` refuses it.)*
3. **Regression caught at build time:** A developer adds a new write/placement seam that composes a mission path from a bare, un-canonicalized handle (or uses the kind-blind resolver for a write). The architectural gate fails CI with a clear message naming the offending call site and the sanctioned seam to use instead. *(Today it sails through every gate.)*
4. **Ambiguous handle:** Any seam handed a handle matching more than one mission raises `MissionSelectorAmbiguous` — never silently picks the first match.

**Primary exception path:** a handle for a mission absent from the resolver (cold-miss) fails closed and loud, never a verbatim passthrough that composes a non-existent literal dir.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `mark_status`'s write leg resolves its target through the same kind-aware authority that its commit leg and `move_task`'s validation use, so the write lands on the surface the validator reads. Closes #2154 (the intra-function write/commit split). | Proposed |
| FR-002 | The `safe_commit` worktree-path policy is surface-aware: it defers to the kind/topology partition and permits a legitimate coordination-owned status write instead of blanket-refusing any `.worktrees/` path staged from the repo root. Closes #2155. | Proposed |
| FR-003 | An architectural call-site gate (the coord-authority discriminator) fails the build when a mission-artifact **write** uses the kind-blind resolver at a site where the kind-aware authority is mandated, unless that site is in a sanctioned allowlist with a recorded rationale. | Proposed |
| FR-004 | An architectural call-site gate (the canonicalizer discriminator) fails the build when an **un-canonicalized handle** reaches the topology-blind primitive `primary_feature_dir_for_mission`. Because the primitive composes the path internally, the gate must scan **calls by name**, not raw `KITTY_SPECS_DIR` joins. Closes the #2164 class by construction. | Proposed |
| FR-005 | Every currently-bypassing canonicalizer call site (the ~34 that pass a bare handle, including `runtime_bridge.py:98/114/139/177` and `decision_log.py:103`) is either routed through the canonical fold `_canonicalize_primary_read_handle` or explicitly sanctioned in the gate's allowlist with a rationale. No un-accounted site remains. | Proposed |
| FR-006 | A parametrized convergence test asserts the read-seam dir equals the write/placement-seam dir for every handle form (full human slug, `<slug>-<mid8>`, bare `mid8`, full ULID, numeric prefix), driven by an injectable/stub resolver so it needs no live `kitty-specs/` fixtures. | Proposed |
| FR-007 | (Fold of #1842, domain-matched) An architectural ratchet forbids literal `/tmp/` path strings in test files, using the same gate pattern this mission introduces. Scope limited to the ratchet; the broader #1842 litter sweep stays out. | Proposed |
| FR-008 | (Fold of #2034, domain-matched) The mission-owned `contract`-marked test files (e.g. `test_mark_status_input_shapes.py`, `test_mark_status_pipe_table.py`) carry a CI-selected co-marker (`fast`/`integration`) so they run. Scope limited to mission-owned files; the `ci-quality.yml` matrix change stays out. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The gate allowlists are **composite-keyed** by `(enclosing_qualname, token_line)` derived live from source, surviving benign line drift. | Zero allowlist churn on edits that do not change a call site's enclosing function or token. | Proposed |
| NFR-002 | Each gate is anti-vacuous: a discovered-row floor plus an in-test self-mutation check (inject a violation → gate FAILS → revert → PASSES). | Both guards present and green for each of the two gates. | Proposed |
| NFR-003 | The gate allowlist is a **shrink-only** governance artifact: a twin staleness guard fails the build if any allowlist entry no longer matches a live call site. | Allowlist entry count is non-increasing across the mission; zero stale entries at merge. | Proposed |
| NFR-004 | The new gates run in the fast test tier. | Each gate completes in < 30 s on the full `src/` tree. | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The guard lives at the **seam in front of** `primary_feature_dir_for_mission`; canonicalization is NEVER folded into the primitive (it calls the primitive to probe — folding in recurses; FR-011, live-confirmed at `_read_path_resolver.py:454`). **Merge-blocker.** | Proposed |
| C-002 | Every patched seam propagates `MissionSelectorAmbiguous` unchanged; no silent first-match (C-009/WP07). Cold-miss fails closed and loud. **Merge-blocker.** | Proposed |
| C-003 | The read-leg handle-safety fix (#2161) is a **pre-condition**, verified, not re-implemented. | Proposed |
| C-004 | Out of scope (do not expand): Phase 2 (the `MissionResolver` DI port), the `ResolvedMission` identity work (#2138, #2139, #1868), and the distinct surfaces #2091, #2100, #2123, #2115. | Proposed |
| C-005 | The gates **copy** the existing Idiom-B machinery (`tests/architectural/test_single_mission_surface_resolver.py` + `surface_resolution_audit/audit.py`) — composite-key allowlist, scan-by-name discriminator, self-test, floor. No new gate mechanism is invented. | Proposed |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A work package advances through `mark_status` → `move_task --to for_review` with no phantom "unchecked subtasks" block (the #2154 reproduction passes). |
| SC-002 | A status transition commits successfully under coordination topology (the #2155 reproduction passes). |
| SC-003 | A deliberately introduced bypass — an un-canonicalized-handle write (FR-004) or a kind-blind write where kind-aware is mandated (FR-003) — fails CI; reverting it passes (each gate's self-test proves this). |
| SC-004 | Zero un-sanctioned bypassing call sites remain: every one of the ~34 canonicalizer sites and the coord-authority write sites is either routed through the canonical authority or sanctioned in an allowlist entry carrying a rationale. |
| SC-005 | The convergence test passes for every handle form with no live filesystem fixtures. |
| SC-006 | No literal `/tmp/` string appears in any test file, and the mission-owned `contract` test files execute in a CI gate. |

## Key Entities

- **Kind-aware resolution authority** — `commit_for_mission(kind=)`, `resolve_planning_read_dir(kind=)`, `resolve_status_surface_with_anchor`: the single sanctioned decider of coord-vs-primary write/read target. *Present today; bypassed by the write leg.*
- **Topology-blind primitive** — `primary_feature_dir_for_mission` (TBYD): composes the literal mission dir, by contract handle-blind. Must remain blind (C-001).
- **Canonical fold** — `_canonicalize_primary_read_handle`: the idempotent handle→canonical-dir-name fold the seam applies before the primitive.
- **Gate allowlists** — composite-keyed, shrink-only governance artifacts recording each sanctioned bypass with a rationale.

## Out of Scope

Phase 2 `MissionResolver` DI port and the broader port family (#2173 Phase 2); `ResolvedMission`/identity strangler work (#1868, #2138, #2139); distinct bug surfaces #2091 (empty-mid8 coord branch), #2100 (inline meta reads), #2123 (lane-prefix over-match), #2115 (pinned `tasks/` dir-read residual). #2140 (`is_committed` surface) is **monitored** — if the canonicalizer gate covers it incidentally, note it; do not pre-commit. Sibling epics #1716/#1868/#1878 are referenced, not merged into scope.

## Assumptions

- The #2161 read-leg fix is landed on `main` (verified pre-condition).
- The Idiom-B gate machinery is copyable as-is (confirmed live; all existing gates green).
- The scope is ~34 canonicalizer call sites + the `mark_status`/`safe_commit` write legs + two gates + two domain-matched test-hygiene folds — a multi-WP mission.
- The mark_status write/commit split is intra-function (`tasks.py:1807` write vs `:1905` commit) — the fix is intra-function, not only cross-command.

## Issue Matrix (pre-planning, 3-squad check)

| Issue | Verdict | Note |
|-------|---------|------|
| #2154 | CLOSE | mark_status write-leg routing (FR-001) |
| #2155 | CLOSE | safe_commit surface-aware guard (FR-002) — must co-land with #2154 |
| #2164 (residual) | CLOSE | the canonicalizer AST gate (FR-004/005); read-leg fix shipped in #2161 |
| #1842 | FOLD (partial) | literal-`/tmp/` ratchet only (FR-007) |
| #2034 | FOLD (partial) | marker co-tag on mission-owned files only (FR-008) |
| #2173 | REFERENCE | epic parent (Phase 1) |
| #2160 | REFERENCE | class this closes (#2154 + #2155) |
| #1619 | REFERENCE | strategic root |
| #1716 / #1868 / #1878 | REFERENCE | sibling epics — not merged |
| #2017 | REFERENCE | guard-friction; incidental, not closed |
| #2136 / #2119 | ALREADY DONE | pre-conditions satisfied (in #2161) |
| #2140 | MONITOR | gate may close incidentally |
| #2138 / #2139 / #2091 / #2100 / #2123 / #2115 | OUT-OF-SCOPE | Phase 2 / ResolvedMission / distinct surfaces / pinned residual |
