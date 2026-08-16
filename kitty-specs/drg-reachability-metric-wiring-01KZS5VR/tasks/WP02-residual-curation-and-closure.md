---
work_package_id: WP02
title: Residual curation, follow-up filing, ticket closure
dependencies:
- WP01
requirement_refs:
- FR-008
- FR-009
- FR-011
planning_base_branch: fix/drg-reachability-metric-wiring
merge_target_branch: fix/drg-reachability-metric-wiring
branch_strategy: Planning artifacts for this mission were generated on fix/drg-reachability-metric-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/drg-reachability-metric-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
history:
- at: '2026-08-11T20:00:00+00:00'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: CHANGELOG.md
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-5
owned_files:
- CHANGELOG.md
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile with `/ad-hoc-profile-load curator-carla` (or read
`packs/built-in/agent_profiles/curator-carla.agent.yaml` and state the directives/tactics you apply). You are
curating doctrine records — accuracy and honest classification are the whole job. Do not delete any valid
artifact; do not manufacture edges.

## Objective

Make the residual-orphan record **true**: give every member of WP01's pinned 75-node residual a disposition,
truth-up the #1923 residual doc, file the three deferred follow-ups as real tracked issues, add the CHANGELOG
entry, and prepare the #3009 + #1923 closure evidence. Depends on WP01 (reflects the final pinned sets).

**Binding (NFR-002 / C-001):** no valid artifact is deleted; only artifacts already retired on disk are
recorded as retired. No metric-gaming.

## Essential context

- The authoritative residual doc is
  `kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md` (NOT inventory-tracked
  — no freshen needed). Read it first; it is stale (lists 14/10 residual orphans from July). **This file is an
  intentional out-of-map edit** — it lives under another mission's `kitty-specs/` dir and cannot be an
  `owned_files` entry (the finalizer forbids `kitty-specs/` paths); edit it with the one-line rationale
  "canonical #1923 residual record, not ownable, updated by this WP." Only `CHANGELOG.md` is owned.
- Read `data-model.md` (residual truth-up section) and `research.md` (the promoted/retired/residual verdicts).
  The final pinned sets come from WP01's `_ACTION_UNREACHABLE_SHIPPED` (75) = `_DEAD_DOCTRINE_SHIPPED` (34) +
  `_PROFILE_DELIVERED_SHIPPED` (41).
- To enumerate the current residual precisely, compute against the wired graph with `.venv/bin/python`
  (see `quickstart.md`).

---

### Subtask T009 — Full residual enumeration + disposition (Debbie #1 totality)

Update the residual doc so **every** member of the 75-node pinned residual is dispositioned — no member rides
along unexamined behind a green pin (the exact failure #3009 was filed against):
- **41 `_PROFILE_DELIVERED_SHIPPED`** — dispositioned **as a group**: "action-unreachable but delivered via
  the profile channel's `{requires, specializes_from, suggests}` web — by design; surfaced when the owning
  profile is active." (List the members; a single group rationale suffices.)
- **34 `_DEAD_DOCTRINE_SHIPPED`** — **FIRST compute the exact 34-member set against the wired graph** (do not
  work from this prose), then bin **each named member** into one disposition (a cluster rationale is allowed
  ONLY where members share a machine-verifiable structural cause — e.g. java-mission-not-activated — and each
  member is still named). Categories: (a) honest activation/runtime-only residual **with note** — e.g.
  `DIRECTIVE_035` (runtime `change_mode: bulk_edit` gate, misfires on every mission if action-scoped),
  `DIRECTIVE_039` (opt-in culture), `migrate-project-guidance-to-spec-kitty-charter` (one-time charter
  migration, **not owned by doctrine-daphne because it is one-time, not a recurring profile procedure** —
  Debbie #7), `deployable-skill-authoring` (no honest static referent; daphne/DIRECTIVE_044/common-docs
  subject-mismatched), `paradigm:atomic-design` (**inert-edge**: only inbound is from a tactic that is itself
  unreachable — NOT wired); (b) by-construction (e.g. `toolguide:powershell-syntax`); (c) inert-chain (a node
  whose only inbound is a dead paradigm/tactic — distinct from referent-less); (d) B2-deferred-with-referent-
  named. **~20 members are not pre-named in the plan — you must name every one.** Explicitly call out the
  **un-clustered singletons** `directive:DIRECTIVE_038` and `procedure:tracker-organisation-workflow` (named
  nowhere in the plan — each needs its own disposition), plus the writing-comms styleguide cluster
  (`plain-language`, `professional-communications`, `publication-authority`, `research-citation-discipline`,
  `docs-accessibility`, `docs-freshness-sla`, `meeting-minutes-format`) and the ~10 dead tactics.
- **`agent_profile:human-in-charge`**: record ONLY under the **incidence** (#1923) residual with its
  runtime-sentinel note. It is a profile seed / traversal root — do NOT list it as a reachability residual
  (Debbie #2).
- **Retire** `toolguide:rtk-search-tooling` — remove its stale row with a retirement note citing removal
  commit `95c5b925a`. **Promote** only the genuinely action-reachable of the former "6 promoted"
  (`decision-marker-capture`, `no-parallel-duplicate-test-runs`, `python-review-checks`,
  `red-main-release-discipline`); `reasons-canvas-writing` + `occurrence-classification-workflow` are
  profile-only (record as profile-delivered); `atomic-design` is a reachability residual (Debbie #4).

### Subtask T010 — File the three deferred follow-ups (real issues, not prose)

Open three tracked issues (via `gh issue create`; `unset GITHUB_TOKEN` if scopes fail) and record their
numbers in the residual doc:
1. **Systemic `operating-procedures → requires` projection** — the structured field exists on ~16 profiles
   (~40 entries) and is projected by no edge builder; a projection would wire all profile-run procedures at
   once. (References this mission's 3 curated tuples as the interim.)
2. **`DISCIPLINED_REFACTORING` vs `procedure:refactoring` consolidation triage** — two artifacts titled around
   disciplined refactoring; a doctrine-authoring decision (A2 linked, did not consolidate).
3. **`quadruple-a` / `DIRECTIVE_041` action-scope traversability** — `quadruple-a` carries an inert edge
   (041 not action-scoped); making 041 action-scoped is a doctrine decision.

### Subtask T011 — CHANGELOG entry

Add a CHANGELOG entry summarizing: the `_ACTION_UNREACHABLE_SHIPPED` reachability companion guard (#3009
point 3), the six genuine wiring edges (88→75 action-unreachable / 38→34 dead), and the #1923 residual
truth-up. Reference #3009 and #1923.

### Subtask T012 — Prepare the ticket-closure evidence (#3009 + #1923)

Draft the closure notes (posted at PR/merge time — do NOT `gh issue close` yet; the operator merges):
- **#3009**: point 1 (membership frozensets) + point 2 (per-node triage) delivered by prior missions; point 3
  (the `reachable_from_actions` companion) delivered here as `_ACTION_UNREACHABLE_SHIPPED` (action-only whole-
  graph, the issue's literal 46%/144 measure) with a both-channel-dead partition. **Reconciliation note**:
  the guard is CI/build-time only (`doctrine doctor` does not surface reachability); both the action-only and
  both-channel-dead sets are now pinned (Alphonso Axis-5 / Debbie #3).
- **#1923**: residual truth-up complete; true residual enumerated + dispositioned; rtk retired; 4 promoted.

### Subtask T013 — Terminology guard + final verification

- `PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q` (doc/prose
  touched).
- Confirm the residual doc's enumerated set matches the graph's true residual exactly; confirm rtk is absent
  from disk + graph; confirm each honest residual carries a rationale.

## Branch Strategy

Planning base + merge target: `fix/drg-reachability-metric-wiring`. Depends on WP01. Execution worktree per
the computed lane from `lanes.json`.

## Definition of Done

- [ ] Every member of the 75-node pinned residual has a disposition (41 group + 34 per-node); no member
      unexamined.
- [ ] `human-in-charge` recorded as incidence-only; `atomic-design` as inert-edge residual; rtk retired; only
      the genuinely action-reachable promoted.
- [ ] Three follow-up issues filed and referenced in the doc.
- [ ] CHANGELOG entry added; #3009 + #1923 closure notes drafted (with the reconciliation note).
- [ ] Terminology guard green; residual doc matches the graph's true residual.
- [ ] **Required evidence (Alphonso Axis-3)**: paste the recomputed residual set (via `.venv/bin/python`
      against the wired graph — see quickstart.md) and show it equals the enumerated doc set URN-for-URN.
      The graph is the single source of truth; the doc is its human-readable projection — prove they agree.

## Reviewer guidance

- Verify the residual doc's set equals the graph's true residual (recompute).
- Verify no valid artifact was deleted (only rtk, already retired on disk, is recorded retired).
- Verify human-in-charge is not miscategorised as a reachability residual, and atomic-design is honestly a
  reachability residual (not "wired").
- Verify the three follow-up issues exist and are referenced.
