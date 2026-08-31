---
work_package_id: WP03
title: Unified resolver seam (ResolvedMissionType bundle)
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-006
- FR-009
- FR-013
- NFR-001
- NFR-002
- NFR-003
- NFR-007
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1464072"
shell_pid_created_at: "1784072007.95"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-03, Lane B critical-path seam)
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/mission_type_profiles.py
- src/charter/__init__.py
- src/runtime/next/prompt_builder.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read: [plan.md](../plan.md) §IC-03 +
"Subsume-not-add" cross-cutting note + "Complexity Tracking", [data-model.md](../data-model.md)
(`ResolvedMissionType` / `ResolvedGovernance` shapes), [contracts/resolution-and-enforcement.md](../contracts/resolution-and-enforcement.md)
C1, and the ADR "Decisions recorded" (one charter-mediated resolver; ordered structured output).
**This is the seam every downstream WP converges on — get the contract exactly right.**

## Objective

Build the **single** charter-mediated entry point
`resolve_mission_type_context(repo_root, *, mission_type=None, feature_dir=None) -> ResolvedMissionType`
that both consumers (`prompt_builder` Surface B and the action-doctrine path via WP04) call — with **no
second resolution path left**. Governance resolves to an **ordered, structured** `ResolvedGovernance`
(type-grain ∪ action-grain, URN-deconflicted). It **subsumes** three existing functions and **migrates
all 7 live call-sites** (subsume-and-migrate, never add-beside — `load_profile` has 0 callers, only the
`__all__` export). `software-dev` resolves as a peer (FR-009), behaviour preserved via a transitional
byte-parity scaffold deleted at this WP's end.

## Context

- The three subsumed functions already live in `charter/mission_type_profiles.py` and are already keyed by
  mission type: `resolve_action_sequence:266`, `resolve_mission_type_governance:325`, `load_profile:175`.
  They are exported in `charter/__init__.py __all__` and have **7 live call-sites** (5 FSM/runtime:
  `runtime_bridge_composition.py:186,319`, `decision.py:601`, `prompt_builder.py:346`; 2 CLI:
  `cli/commands/mission_type.py:1477`, `charter/activate.py:152`, `charter/mission_type.py:82` — grep-repin
  live). **`load_profile` has 0 callers** — it is only the `charter/__init__.py __all__` export, so its
  disposition is export-removal, not a call migration.
- **`mission_type.py:1477` is now in-scope for WP03** (dep edge WP01 → WP03 added): WP01 lands first and
  removes the `governance_refs` display rows from that file, so WP03 migrates the `resolve_action_sequence`
  call-site (+ its import) as a **justified out-of-map, sequential** edit on the now-quiet file. No
  operator-deferred caller remains.
- Two **distinct hard-fail policies** must be preserved as explicit branches: action-sequence validates
  against the activation set with no escape hatch; governance **tolerates** an unknown type when a
  project override exists (`:392`). Do not flatten them. The resolver **already raises
  `UnknownMissionTypeError` on an unknown type today** (it does NOT default to software-dev) — preserve
  that behaviour verbatim through the subsume; do not regress it.
- The `expected_artifacts` slot is populated by **WP10** (after the upward reconcile), not here — leave it
  reserved. `template_set` slot is a later slice.
- Complexity ceiling: keep `resolve_mission_type_context` ≤ 15 via extracted `_resolve_type_key` /
  `_resolve_governance_slot` / `_resolve_action_slot` helpers — not a flat function.

## Subtask guidance

- **T012 — bundle types.** Define `ResolvedMissionType` and `ResolvedGovernance` per data-model.md.
  Governance selections are **ordered `list[URN]`** with an explicit, tested sort (NFR-007) — not sets.
  Include `provenance` (builtin|org|project) on the governance layer; reserve `expected_artifacts`,
  `template_set` slots (populated later / by WP10).
- **T013 — resolver + helpers.** Implement `resolve_mission_type_context`: type key resolution (explicit
  arg → `feature_dir/meta.json` → error) via the WP02 canonicalizer, then governance slot, action slot,
  step-contract slot (WP11 wires the step source through this bundle). Extract the three `_resolve_*`
  helpers to hold complexity ≤ 15.
- **T014 — subsume.** Fold `resolve_action_sequence` / `resolve_mission_type_governance` / `load_profile`
  into the resolver. A former function is kept **only** where it is genuinely the right long-term API —
  never as a wrapper retained solely to avoid editing callers (C-002, ADR).
- **T015 — migrate 7 call-sites + `__all__` + stale doc refs.** Migrate all 7 live call-sites onto the
  resolver and disposition the `charter/__init__.py __all__` exports (`load_profile` → export-removal,
  0 callers). **You own** `prompt_builder.py:346` (Surface B rewire) and `charter/__init__.py`. The other
  call-sites live outside owned_files — migrate them as **justified out-of-map** edits, **including
  `cli/commands/mission_type.py:1477` (+ its import)**: WP01 lands first (dep edge) and has already removed
  the `governance_refs` display rows there, so this is a sequential quiet-file edit — no deferred caller
  remains. Also update the **stale docstring cross-reference at `src/charter/resolver.py:299`** (it
  references `resolve_mission_type_governance`) as a justified out-of-map edit, so the subsume leaves no
  dangling doc ref / reviewer red-herring. Record every out-of-map site in the PR body.
- **T016 — disjointness guard (FR-013).** Union type-grain ∪ action-grain and **forbid** the same artifact
  in both grains, compared on **canonical URN** (normalize `003-…` / `DIRECTIVE_003` / URN before
  comparison). A double declaration is a **construction-time error**, not silent de-duplication.
- **T017 — hard-fail policies + empty grain.** Preserve the two hard-fail policies as explicit branches;
  an **unknown typed** mission raises a clear `UnknownMissionTypeError`-class error on every path (FR-003).
  **PRESERVE the existing `UnknownMissionTypeError`** — `mission_type_profiles.py` already hard-fails on an
  unknown type (it does NOT default to software-dev); the subsume must carry that raise through unchanged,
  not re-introduce a fallback. A **known type with an empty grain** resolves to an empty set without error (FR-004).
- **T018 — parity scaffold + determinism.** Add a **transitional** sw-dev byte-parity scaffold proving
  resolved governance text is unchanged for a software-dev mission (FR-009/NFR-001), then **delete it in
  this WP's final commit** (it is transitional — do not merge it). Add an **enduring** determinism test
  (two resolutions → byte-identical, NFR-007). `ruff` + `mypy` clean; complexity ≤ 15.

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It depends on **WP01** (quiet-file predecessor for the
`mission_type.py:1477` out-of-map edit) and **WP02** (canonicalizer), and is the parent of
WP04/WP05/WP06/WP07/WP08/WP11/WP12.

## Definition of Done

- [ ] `resolve_mission_type_context(...)` is the sole resolution entry point; **0** call-sites remain on the
      three subsumed functions — **no exception** (`mission_type.py:1477` is migrated here; `load_profile`
      export removed).
- [ ] `ResolvedGovernance` selections are ordered lists with a tested sort; determinism test green (NFR-007).
- [ ] Cross-grain double-declaration raises at construction time on canonical-URN comparison (FR-013).
- [ ] Unknown-typed mission hard-fails on every governance path via the **preserved** `UnknownMissionTypeError`
      (no re-introduced sw-dev fallback, FR-003); known-empty-grain resolves empty without error (FR-004).
- [ ] `charter/__init__.py __all__` dispositioned (subsume-and-migrate, no add-beside); stale docstring
      cross-ref at `charter/resolver.py:299` updated (no dangling `resolve_mission_type_governance` ref).
- [ ] Transitional sw-dev byte-parity scaffold added AND deleted in this WP (0 survives).
- [ ] `resolve_mission_type_context` complexity ≤ 15 (helper-extracted); `ruff` + `mypy` clean.

## Risks

- **A third resolution path entrenched** if any of the 7 call-sites is left on the old functions. The
  disposition must be exhaustive and reviewer-verified.
- **Complexity blow-out** — resolve via the three named helpers, not a flat branch tree.
- **Flattening the two hard-fail policies** — keep them as explicit, separately-tested branches.
- **Merging the parity scaffold** — it is transitional; it MUST be deleted in this WP's final commit.

## Reviewer guidance (reviewer-renata, opus)

- Grep for residual imports/calls of the three subsumed functions across the tree (**expect 0** — incl.
  `mission_type.py:1477`, migrated here; and no stale doc ref at `charter/resolver.py:299`).
- Confirm the disjointness guard compares **canonical URNs**, not raw strings.
- Confirm the byte-parity scaffold is gone at HEAD and the determinism test is enduring (doctrine-module).
- Confirm complexity ≤ 15 on `resolve_mission_type_context` and each `_resolve_*` helper.

## Activity Log

- 2026-07-14T22:38:29Z – claude:sonnet:python-pedro:implementer – shell_pid=1366440 – Assigned agent via action command
- 2026-07-14T23:32:19Z – claude:sonnet:python-pedro:implementer – shell_pid=1366440 – Ready: unified resolve_mission_type_context seam; 0 survivors (7 call-sites migrated + load_profile export removed); URN cross-grain disjointness guard (FR-013); two hard-fail policies preserved as explicit branches; typeless neutral degrade; complexity <=15; parity scaffold added+deleted
- 2026-07-14T23:33:35Z – claude:opus:reviewer-renata:reviewer – shell_pid=1464072 – Started review via action command
- 2026-07-14T23:43:34Z – user – shell_pid=1464072 – Review PASSED (approved via --force; see rationale). Blocking staged file .kittify/charter/synthesis-manifest.yaml + untracked .kittify/doctrine/* are an UNRELATED parallel charter-authoring stream (separate forked session), NOT WP03 deliverables: outside owned_files, outside the diff, absent from WP03 commit b5b407c47 (git show --stat under .kittify empty). Committing them into WP03 would be a scope leak; --force avoids that. WP03 verdict: 0-survivor confirmed (only prose/docstring refs remain; zero live callers/imports of resolve_action_sequence/resolve_mission_type_governance/load_profile); 7 call-sites migrated to bundle.action_sequence with arg-order + catch/degrade preserved; load_profile export removed, __all__ dispositioned (no wrapper); new seam has 7 live callers. FR-013 canonical-URN disjointness guard, 3 forms tested. NFR-007 determinism (ordered sorted lists + enduring byte-identical test). FR-003/003a/004 tolerant(governance)/strict(action) hard-fail branches preserved; UnknownMissionTypeError carried through; typeless->neutral. Eager-both design judged SOUND (action []-degrade required for override-tolerance to be meaningful; strict raise intact for registered-but-undefined; WP04 can still thread action_grain). Parity scaffold 0 survivors; golden tests updated to seam (not deleted-to-green). Gates: ruff C901=0, ruff=0, mypy --strict src/charter=0, pytest charter+next=1757 passed/1 skipped. resolver.py:299 docstring cross-ref updated. Out-of-map edits justified per WP dep edges.
- 2026-07-14T23:46:38Z – user – shell_pid=1464072 – Review passed (reviewer-renata, verdict MET): 0-survivor subsume + eager-both sound + URN disjointness + determinism + gates green. --force: deliverables committed in b5b407c47; worktree dirt is an unrelated forked session (PID 348359) re-staging .kittify/doctrine, excluded from scope.
