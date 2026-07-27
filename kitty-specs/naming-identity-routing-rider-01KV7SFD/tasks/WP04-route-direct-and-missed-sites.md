---
work_package_id: WP04
title: Route direct mid8 sites + scope-review additions
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-009
tracker_refs: []
planning_base_branch: feat/naming-rider-3-2-1
merge_target_branch: feat/naming-rider-3-2-1
branch_strategy: Planning artifacts for this mission were generated on feat/naming-rider-3-2-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/naming-rider-3-2-1 unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1940279"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/test_mid8_direct_routing.py
execution_mode: code_change
owned_files:
- src/specify_cli/git/sparse_checkout.py
- src/specify_cli/doctrine_synthesizer/apply.py
- src/specify_cli/context/mission_resolver.py
- src/runtime/next/_internal_runtime/retrospective_terminus.py
- src/mission_runtime/resolution.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/retrospective/generator.py
- tests/specify_cli/test_mid8_direct_routing.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read `spec.md`, `plan.md` (IC-02), `research.md`, and `scope-review/paula-missed-paths.md` (the 5
var-name-independent shapes).

## Objective

Route the **guaranteed-full-id direct sites** and the **5 shapes the first grep missed** through
`resolve_mid8`, verify there is **no `ExecutionContext`-held re-derivation** (FR-002), and delete the
shadows (verification-by-deletion). Depends on WP01.

## Context

These sites hold a non-empty `mission_id` (or a slug) and do not need the `""`/`None` special handling of
WP03 — but route through `resolve_mid8` anyway (the public door, FR-010), passing the slug they have (or
`""`). For a site with only a full `mission_id`: `resolve_mid8("", mission_id=full)` == old `mid8(full)`
(WP01 guarantees this).

## Subtasks

### T011 — Direct sites (use resolve_mid8)
Route each, preserving output:
- `git/sparse_checkout.py:286` — `mid8 = _mid8(mission_id)` → `resolve_mid8(<slug or "">, mission_id=mission_id)`.
- `doctrine_synthesizer/apply.py:745` and `:831` — `mid8=...` kwargs.
- `context/mission_resolver.py:163` — `mid8=...`.
- `runtime/next/_internal_runtime/retrospective_terminus.py:69` — `return ...`.

### T012 — The 5 scope-review additions (var-name-independent shapes)
These hid behind `str()`/intermediate vars and escaped the `*_id[:8]` grep — confirm each is a
**mission-identity** derivation (NOT `invocation_id` or a sha), then route:
- `mission_runtime/resolution.py:171` — `return str(raw_mission_id)[:8]` (`_mid8_from_primary_meta`, a core
  read-path producer — route via `resolve_mid8`, preserving its decline/empty behavior).
- `cli/commands/agent/mission.py:772` — `mid8 = raw_mid[:8] if isinstance(raw_mid, str)...` (feeds
  `CoordinationWorkspace.resolve` — load-bearing; preserve the guard semantics).
- `cli/commands/mission_type.py:643` — `return mission_id_meta[:8] if len(...) >= 8 else ""`.
- `cli/commands/agent/workflow.py:292` — `mid[:8]`.
- `retrospective/generator.py:112` — `mid[:8]`.

### T013 — Verify FR-002 (no fragment re-derivation)
Confirm (and add a test asserting) that no site holding an `ExecutionContext`/`ActionContext` re-derives
mid8 — the inventory found zero; pin it so a future regression is caught.

### T014 — Delete shadows + verification-by-deletion
Remove all inline derivations in this WP's files; run the full suite — green proves the seam is the only
path.

## ⚠️ Post-tasks remediation (binding — see tasks-review/POST-TASKS-SYNTHESIS.md)

- **Lands BEFORE WP01.** Route to the already-public `resolve_mid8`; do not reference `_mid8`.
- **`retrospective_terminus.py` is a SHADOW DEF, not a one-line route:** there is a local
  `def _mid8(mission_id)` at `:67` with caller(s) (`:137`). **Delete the local shadow def** and route its
  caller(s) to `resolve_mid8`. DoD: `grep -n "def _mid8" src/runtime/next/_internal_runtime/retrospective_terminus.py`
  returns nothing (delete the def, don't just edit line 69).
- **`retrospective/generator.py:112` is a SELECTOR COMPARISON, NOT a derivation:**
  `if mid == mission_handle or mid[:8] == mission_handle or slug == mission_handle:` — it prefix-matches a
  candidate `mission_id` against a handle. Do **not** naively route it through `resolve_mid8` (changes
  semantics). Either preserve the comparison (compute the canonical mid8 once, then compare) **or exclude
  it** and hand it to WP02's allow-list with the justification "mission-resolution prefix-match, not a name
  compose." Record the decision.
- **`mission_type.py:643` is contract-sensitive** (`… else ""`) — use `resolve_mid8`'s `""`-decline
  contract, not a naive route.
- **FR-002 test (T013):** construct a **real `ExecutionContext`** and assert no mid8 re-derivation while
  holding it (not a stub). Record each of the 5 additions' mission-identity provenance in the test/PR note.
- **Byte-parity (anti-gaming):** golden values are **literals captured from HEAD before any edit**.

## Branch Strategy
Base/merge target: `feat/naming-rider-3-2-1`. Worktree from `lanes.json`.

## Definition of Done
- [ ] All direct sites + the 5 additions route through `resolve_mid8`; outputs byte-identical (NFR-001).
- [ ] Each addition confirmed mission-identity (not a foreign id); `resolution.py:171` decline/empty
      behavior preserved.
- [ ] FR-002 verification test added.
- [ ] Shadows deleted; suite green (verification-by-deletion).
- [ ] `ruff`/`mypy` clean on diff; complexity ≤ 15; no suppressions.

## Risks / reviewer guidance
- **`agent/mission.py` is a 3k-line god-module** — change ONLY line ~772; do not refactor the module
  (out of scope; #1623-class).
- `resolution.py:171` is a core read-path producer — be careful its decline/empty contract is preserved
  (it feeds the read path; a behavior change here ripples).
- Do NOT touch `test_no_worktree_name_guess.py` (WP02 owns it, lands after).

## Activity Log

- 2026-06-16T12:21:48Z – claude:opus:python-pedro:implementer – shell_pid=1872243 – Assigned agent via action command
- 2026-06-16T12:37:18Z – claude:opus:python-pedro:implementer – shell_pid=1872243 – Routed direct sites + 5 additions; deleted retrospective_terminus shadow _mid8 def; generator.py:112 handled as selector-comparison (decision noted); FR-002 real-ExecutionContext test; golden-from-HEAD; ruff+mypy clean.
- 2026-06-16T12:38:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=1940279 – Started review via action command
- 2026-06-16T12:41:35Z – user – shell_pid=1940279 – Review passed: 9 sites routed; terminus shadow _mid8 deleted; generator.py:112 selector preserved (option A, false-match test); agent/mission.py one-line; resolution.py decline preserved; 19 HEAD-literal tests + real-ExecutionContext FR-002; ruff+mypy clean (pre-existing failures confirmed); no _mid8 ref.
