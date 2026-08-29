---
work_package_id: WP09
title: Durability gates 1-3 (AgentProfileRepository, DoctrineService, resolver imports)
dependencies:
- WP01
- WP02
- WP03
- WP05
requirement_refs:
- FR-007
- NFR-001
- NFR-003
planning_base_branch: feat/charter-sole-door-bypass-closure
merge_target_branch: feat/charter-sole-door-bypass-closure
branch_strategy: Planning artifacts for this mission were generated on feat/charter-sole-door-bypass-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-sole-door-bypass-closure unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
phase: Phase 3 - Durability (must run after WP01/02/03/05)
history:
- at: '2026-08-03T14:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-08-03T15:00:00Z'
  actor: system
  action: Post-tasks squad restructure - Gate 4 moved to WP06, Gate 5 moved to WP04 (paula-patterns finding, both gates only ever guarded their own WP's surface); dropped the false "WP05 closed the one real consumer" claim for Gate 3 (debugger-debbie finding - nothing outside src/charter/** ever imported doctrine.resolver, so Gate 3 is a forward-looking regression guard, not proof of a closure); corrected Gate 2's exclusion line numbers and qualname-resolution requirement (reviewer-renata, debugger-debbie findings); dependency on WP06/WP08 dropped since their gates left with them
agent_profile: architect-alphonso
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_charter_sole_door_agent_profile_repository.py
- tests/architectural/test_charter_sole_door_doctrine_service.py
- tests/architectural/test_charter_sole_door_resolver_imports.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_charter_sole_door_agent_profile_repository.py
- tests/architectural/test_charter_sole_door_doctrine_service.py
- tests/architectural/test_charter_sole_door_resolver_imports.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – Durability gates 1-3

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `architect-alphonso` (implementer role, claude agent) before
parsing the rest of this prompt — non-vacuous gate construction is a structural-integrity concern.

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` in the event log before starting. Address all feedback; log changes in the Activity Log.

---

## Objectives & Success Criteria

Ship non-vacuous, zero-tolerance architectural gates for the three bypass categories that are genuinely
cross-cutting across multiple WPs (FR-007). **Gates 4 and 5 moved to WP06 and WP04 respectively** — a
post-tasks squad found they only ever guarded those WPs' own surfaces, so a separate WP for them added a
dependency edge with no real benefit. This WP must run AFTER WP01, WP02, WP03, WP05 land.

**Success criteria** (NFR-001, NFR-003):
- Each gate resolves the **bound qualname** of the offending construct (via import resolution, not text
  matching) — a text-only grep cannot distinguish `charter.activation.resolver.DoctrineService(inner,
  pack_context=None)` (sanctioned) from a raw `doctrine.service.DoctrineService(...)` (forbidden).
- The `.kittify/profiles` (Gate 1) and `_doctrine_collect.py` unfiltered-mode (Gate 2) exclusions are keyed
  by **composite identity** (file + qualname + line), never a whole-file exclusion.
- Every self-mutation proof injects its violating construct at **function-local or nested (`try`/`except`)
  scope** — matching the actual shape of the real violations found; module-level-only injection does not
  prove non-vacuity (the exact WP10 lesson from `doctrine-charter-split-unification-01KZ0SRB`).
- Frozen **zero-tolerance** baselines — no shrink-only allowlist (C-002).

## Context & Constraints

- **Depends on WP01, WP02, WP03, WP05** (declared in frontmatter). Do not start until all four have landed
  — writing these gates earlier produces either false-green or false-red results.
- **Gate 2's exclusion sites** (`_doctrine_collect.py`'s unfiltered-mode constructions) are at **lines
  193, 283, 420, 828** — post-tasks squad verified these against current code; the original citations
  (191/281/418/826) had drifted +2 lines. Re-verify against the actual file state in your worktree before
  hardcoding — WP03 will have landed by the time this WP runs, and its own edits may have shifted lines
  again.
- **Gate 2 must also NOT flag `org_layer.py`/`generate.py`** — WP01 retargets those onto the unified
  builder, which internally constructs the raw service before wrapping it; confirm the gate resolves to the
  builder's internal construction (sanctioned, inside the builder function itself) vs. a caller constructing
  raw `DoctrineService` directly (forbidden).
- **Gate 3 is a forward-looking regression guard, not proof of a fix** (post-tasks squad correction — the
  original prompt claimed "WP05 closed the one real consumer," which is false: nothing outside
  `src/charter/**` ever imported `doctrine.resolver`). Write it as: "no module outside `src/charter/**` or
  `src/doctrine/**` may import `doctrine.resolver`" — a durability guard against a future regression, not a
  claim about what this mission changed.
- Extend `tests/architectural/test_org_activation_seam.py` and `tests/architectural/test_layer_rules.py`
  where their existing coverage is adjacent; do not re-assert what they already prove.

## Branch Strategy

- **Strategy**: lane-per-WP (normalized by `finalize-tasks`)
- **Planning base branch**: feat/charter-sole-door-bypass-closure
- **Merge target branch**: feat/charter-sole-door-bypass-closure

## Subtasks & Detailed Guidance

### Subtask T037 – Gate 1: `AgentProfileRepository` zero-tolerance

- **Purpose**: Close FR-001's category durably.
- **Steps**:
  1. AST-walk all of `src/` for `AgentProfileRepository(` construction calls, resolving each to its bound
     import.
  2. Zero-tolerance: fail on any match outside `src/charter/activation/resolver.py`, WP01's unified builder, and the
     two composite-key-excluded `.kittify/profiles` sites (`registry.py:48`, `profiles_cmd.py:83`) —
     excluded by exact file+line, not by filename alone.
  3. Self-mutation proof: inject a new `AgentProfileRepository(` construction at function-local scope in a
     scratch module; assert the gate fails naming the exact line.
- **Files**: `tests/architectural/test_charter_sole_door_agent_profile_repository.py` (new).
- **Parallel?**: Yes, alongside T038-T039.

### Subtask T038 – Gate 2: `DoctrineService` zero-tolerance, qualname-resolving

- **Purpose**: Close FR-002/FR-008's category durably, correctly distinguishing the two classes.
- **Steps**:
  1. AST-walk all of `src/` for `DoctrineService(` construction calls; resolve each to its bound import
     (`doctrine.service.DoctrineService` vs `charter.activation.resolver.DoctrineService`).
  2. Zero-tolerance on raw `doctrine.service.DoctrineService(` outside `src/charter/activation/resolver.py` and WP01's
     unified builder function's own body.
  3. The 4 `_doctrine_collect.py` unfiltered-mode sites — verify current line numbers in your worktree, do
     not assume 193/283/420/828 still holds after WP03's edits — are sanctioned; exclude by composite key
     (file+qualname+line), confirming each genuinely uses `pack_context=None`.
  4. Self-mutation proof: inject a raw `doctrine.service.DoctrineService(` construction at function-local
     scope; assert the gate fails.
- **Files**: `tests/architectural/test_charter_sole_door_doctrine_service.py` (new).
- **Parallel?**: Yes.

### Subtask T039 – Gate 3: `doctrine.resolver` direct-import, forward-looking regression guard

- **Purpose**: Ensure no FUTURE consumer outside `src/charter/**`/`src/doctrine/**` starts importing
  `doctrine.resolver` directly — a durability guard, not proof of a WP05 closure (there was no such
  violation to close; see Context above).
- **Steps**:
  1. Scan `src/` for `from doctrine.resolver import ...` / `import doctrine.resolver` outside
     `src/charter/**` and `src/doctrine/**`.
  2. Zero-tolerance — no exclusions expected.
  3. Self-mutation proof: inject a direct import at function-local scope in a scratch module outside
     `src/charter/**`; assert the gate fails.
- **Files**: `tests/architectural/test_charter_sole_door_resolver_imports.py` (new).
- **Parallel?**: Yes.

## Test Strategy

- `pytest tests/architectural/ -k "charter_sole_door" -v` — all 3 gates in this WP plus WP04's Gate 5 and
  WP06's Gate 4 (run the full family together at least once to confirm no interaction).
- Confirm each gate's self-mutation proof actually fails when run against the mutated scratch module.

## Risks & Mitigations

- **Writing a gate that only scans module-level imports/constructs.** Every self-mutation proof MUST inject
  at function-local/nested scope.
- **Assuming line numbers instead of re-verifying.** WP03 edits `_doctrine_collect.py`; re-check its current
  state in your worktree before hardcoding Gate 2's exclusion lines.
- **Claiming Gate 3 proves a closure.** It does not — state it as a forward-looking guard only.

## Review Guidance

- Confirm every self-mutation proof was actually run and observed failing.
- Confirm no gate uses a bare text `grep`/string-match — all resolve qualnames via AST/import resolution.
- Confirm Gate 2's exclusion lines match the CURRENT `_doctrine_collect.py`, not the original (possibly
  stale) citation.
- Confirm the PR description does not claim Gate 3 as evidence of a bypass closure.

## Activity Log

- 2026-08-03T14:10:00Z – system – Prompt created.
- 2026-08-03T15:00:00Z – system – Post-tasks squad restructure: dropped Gates 4/5, corrected scope/claims.
- 2026-08-03T20:55:38Z – claude – shell_pid=352727 – WP09 escalated C-002 finding 1/3 (Gate 1, NOT pre-sanctioned): tool_surface/profiles/projection.py default_profile_repository is excluded by composite key (file+qualname+token) because .kittify/agent_profiles project-overlay profiles are unreachable through the unified builder - resolve_project_root offers only .kittify/doctrine, src/doctrine, doctrine, and build_activation_aware_doctrine_service has no parameter to retarget the inner project dir. Confirmed independently by WP02's implementer and reviewer (both forced the naive migration and reproduced 3 real test breakages). This is a TRACKED FOLLOW-UP requiring a future WP01 builder-level project-overlay override, NOT a permanent carve-out: the exclusion entry must be DELETED, not renewed, once that override exists. Recorded in the gate module docstring and in the descriptor's rationale field.
- 2026-08-03T20:55:57Z – claude – shell_pid=352727 – WP09 escalated C-002 findings 2/3 and 3/3 (Gate 2, NOT pre-sanctioned): cli/commands/_doctrine_asset.py _build_asset_repository and charter/compiler.py _default_doctrine_service both construct the raw doctrine.service.DoctrineService locally and wrap it immediately. That is exactly the remedy FR-002 prescribed ('routing each through charter.activation.resolver.DoctrineService'), delivered by WP03 which is approved, and both carry in-code rationale. But it does not satisfy NFR-001's stricter locality phrasing ('zero matches ... outside src/charter/activation/resolver.py and the one unified builder'). This is a spec-internal tension between FR-002's remedy and NFR-001's wording, NOT an unresolved bypass - reported here rather than silently absorbed. Mitigation: Gate 2 enforces TWO policies. Policy A (no allow-list whatsoever) asserts no raw service escapes unwrapped and is the real FR-002 invariant; Policy B enforces NFR-001's locality with 6 named composite-key exclusions, each CONDITIONAL on Policy A still holding at that site, so deleting the wrap reds the gate. Operator decision needed only on whether to later fold these two onto the unified builder.
- 2026-08-03T20:56:14Z – claude – shell_pid=352727 – WP09 deviations from the prompt letter, each deliberate and justified. (1) Exclusions are keyed (file, qualname, token) via the canonical specify_cli.contracts.anchoring ContentDescriptor, NOT (file, qualname, line) as spec.md NFR-001 phrases it: raw line numbers are BANNED as authoritative comparands anywhere under tests/architectural/ by the standing gate test_ratchet_positional_anchor_ban.py (DIR-041 / #2077, mission content-address-ratchet-allowlists-01KX8M4D). Seeding (rel, N) rows would have red that gate. Content anchoring is strictly stronger, and this mission proved the drift empirically - EVERY line number spec.md pinned had already moved: registry.py 48->73, projection.py 84->115, profile_resolution.py 81->95, _doctrine_collect.py 193/283/420/828 -> 209/314/468/920. Verified test_ratchet_positional_anchor_ban.py passes with the new gates in place. (2) Gate 1 has FOUR named exclusions, not the two the prompt cites: the two .kittify/profiles C-006 sites, PLUS charter/profile_resolution.py _default_agent_profile_repository (pre-sanctioned verbatim by spec.md FR-001 as a confirmed bootstrap carve-out, which the prompt's summary omitted), PLUS the escalated projection.py site. (3) Gate 2's Policy A also polices a SECOND acquisition route this WP's sweep found: org_layer.py obtains an unwrapped raw service by CALLING charter.activation.doctrine_service_builder._build_doctrine_service rather than constructing the class, so a construction-only gate would not notice a future non-wrapping caller. Charter-internal builder callers stay exempt per the builder's documented contract. (4) Merged the four approved dependency lanes (WP01/WP02/WP03/WP05) into lane-h - none had reached it, so the gates were unwritable and unverifiable; only rematerializable status.json conflicted.
- 2026-08-03T21:23:50Z – claude – shell_pid=352727 – WP09 full tests/architectural run: 1633 passed, 3 failed, 2 skipped, 2 xfailed. All three failures attributed by running them on the mission merge-base (457940064) in a throwaway worktree. (1) test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline - PASSES on merge-base, so it was MINE: the 3 new gate files pushed tests/architectural's convert-classified golden-count census 23->39. FIXED by converting all 16 sites to content assertions (qualname list/set equality) rather than re-freezing the baseline or blanket-annotating with the cardinality-is-contract escape hatch; census is back to exactly the frozen ceiling of 23 with zero contribution from WP09. (2) test_marker_baseline::test_marker_set_does_not_grow_vs_baseline - PASSES on merge-base, so it is INHERITED FROM WP02: its tests/perf/test_tasks_status_baseline.py carries pytestmark=[pytest.mark.slow] but its two node ids were never added to tests/architectural/marker_baseline.txt. Outside WP09's write scope (WP02's file + a baseline WP09 does not own). This does NOT self-resolve at merge - marker_baseline.txt is a committed baseline, so the gate stays red and will red CI once lanes consolidate. Needs a deliberate regeneration with a rationale comment, per that gate's own docstring. (3) test_inline_meta_read_gate::test_routed_load_meta_floor - FAILS ON THE MERGE-BASE TOO (routed load_meta census 110 vs floor 117), so it is a pre-existing mission-branch red owned by neither WP09 nor any lane. Per the charter's pre-existing-failure reporting rule: reported, not green-washed.
