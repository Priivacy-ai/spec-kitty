---
work_package_id: WP02
title: 'Ratchet: AST short-id detector + failover-bypass rule'
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-010
tracker_refs: []
planning_base_branch: feat/naming-rider-3-2-1
merge_target_branch: feat/naming-rider-3-2-1
branch_strategy: Planning artifacts for this mission were generated on feat/naming-rider-3-2-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/naming-rider-3-2-1 unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2008491"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_no_worktree_name_guess.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read `spec.md` (FR-004/FR-010), `plan.md` (IC-01), and `scope-review/paula-missed-paths.md` +
`alphonso-scope-boundary.md` (the ratchet is a tripwire, not the proof).

## Objective

Add the regression **tripwire**: a new AST short-id slice detector + a failover-bypass rule to
`tests/architectural/test_no_worktree_name_guess.py`. **This WP lands LAST** (depends on WP03/WP04/WP05) —
by then the routed sites are gone, so the allow-list is empty/minimal and there is no per-WP allow-list
coordination. **You are the sole editor of this test.**

## Context (honest scoping — binding)

- The test today detects name *composes*, NOT slices — the short-id detector is **new code**.
- AST cannot structurally tell `mission_id` from `invocation_id`, so detection rests on a **name
  allow-list / heuristic**; this is a **tripwire, not a completeness oracle**. **Verification-by-deletion
  (the suite staying green after WP03/WP04 deleted the shadows) is the real correctness guarantee.**
- It is defeated by helper indirection (`mid[:8]` via a function); state this limit in the test.

## Subtasks

### T018 — AST short-id slice detector
Walk `src/` ASTs for a subscript-slice `<expr>[:8]` / `[0:8]` where `<expr>` is a name/attr matching the
mission-identity shape (`mission_id`, `mid`, `raw_mid`, `*_id_meta`, and `str(<id>)[:8]` calls). Cover
`src/specify_cli/dashboard/scanner.py` explicitly. The detector must catch the 5 shapes Paula found
(string-wrapped, intermediate-var, `_meta`-suffixed).

### T019 — Failover-bypass rule
Flag a correctness-path mid8 derivation that bypasses the failover entrypoint: bare `_mid8(...)` (the
now-private primitive) or an inline `[:8]` slice OUTSIDE `branch_naming.py` / `mission_runtime/context.py`
(the sanctioned single-derivation homes). The sanctioned path is `resolve_mid8`.

### T020 — Minimal allow-list + non-target + honesty note
- Seed an allow-list as an **empty (or near-empty) module-level frozenset** — by now WP03/WP04/WP05 have
  removed the sites. Any remaining entry must carry an inline justification.
- Ensure `src/specify_cli/invocation/executor.py:469` (`invocation_id[:8]`, a different identity domain)
  does NOT trip the detector (name specificity, or one justified allow-list entry).
- Add a module docstring honesty note: this is a **syntax-level tripwire**, defeated by helper
  indirection; it explicitly does **not** cover the deferred `feature_dir.parent.parent` repo-root
  derivation class (~9 sites, owned by the read-path follow-on focus).

### T021 — Guard self-test
Add a test that plants a bare `mission_id[:8]` (e.g. in a temp fixture / via a controlled string) and
asserts the detector flags it; and that the clean tree passes. Confirm the allow-list shrank vs the
pre-mission baseline.

## ⚠️ Post-tasks remediation (binding — see tasks-review/POST-TASKS-SYNTHESIS.md)

- **Depends on WP01 now** (lands after the `mid8`→`_mid8` rename), so the bypass rule references the final
  `_mid8`. By then WP03/04/05 have removed every consumer slice.
- **NOT "empty allow-list" — carve out file-level HOMES (F-2).** Two permanent sanctioned slice homes are
  skipped at FILE level via the existing `_SEAM_REL` home-skip: `src/specify_cli/lanes/branch_naming.py`
  (`_mid8`/`resolve_*` legitimately keep `mission_id[:8]`) and `src/mission_runtime/context.py`
  (`IdentityFragment`, "here and nowhere else"). `invocation/executor.py:469` (`invocation_id[:8]`) is
  excluded by name. The correct claim is: **the mission-identity CONSUMER class is empty; the homes
  remain.**
- **T018 inner-name predicate must be SUBSTRING/glob (`*mission_id*`), not exact-match** — otherwise
  `str(raw_mission_id)[:8]` (operand `raw_mission_id`) escapes and the original blind spot returns.
- **T021 self-test plants ALL 5 shapes** (`mission_id[:8]`, `str(raw_mission_id)[:8]`, `mid[:8]`,
  `raw_mid[:8]`, `…_id_meta[:8]`) and asserts EACH is flagged, **and** asserts `invocation_id[:8]` is NOT
  flagged. Pin the pre-mission baseline slice-count as a **committed literal** so "shrank to 0 consumers"
  is objective (a brand-new detector has no prior baseline otherwise).
- **`retrospective/generator.py:112`**: if WP04 excluded it (selector prefix-match), add it as a single
  justified allow-list entry; if WP04 routed it, no entry.

## Branch Strategy
Base/merge target: `feat/naming-rider-3-2-1`. Worktree from `lanes.json`.

## Definition of Done
- [ ] AST detector catches the 5 var-name-independent shapes incl. `dashboard/scanner.py`.
- [ ] Failover-bypass rule flags correctness-path bypasses of `resolve_mid8`.
- [ ] Allow-list empty/minimal & justified; `invocation_id[:8]` not tripped; honesty note + deferred-class
      note present.
- [ ] Guard self-test green; clean tree passes.
- [ ] `ruff`/`mypy` clean; complexity ≤ 15; no suppressions.

## Risks / reviewer guidance
- **Reviewer:** confirm the test is honestly scoped (no overclaim of "cannot regrow"); confirm it does not
  false-positive on `invocation_id[:8]` or legitimate non-identity `[:8]` slices; confirm the allow-list
  actually shrank.
- This is the SOLE form-coupled test in the mission — that's intentional and correct.

## Activity Log

- 2026-06-16T13:11:29Z – user – shell_pid=1996947 – Unblock after manual lane-a->lane-b merge (plan.md add/add resolved to integration version ddf5c259; merge commit bdaa64531). Transient worktree_alloc_failed cleared; resuming implement.
- 2026-06-16T13:19:02Z – claude – shell_pid=1996947 – AST short-id detector (substring predicate catches all 5 shapes incl str(raw_mission_id)[:8]) + failover-bypass rule; seam HOMES carved file-level; doctor.py tolerance allow-listed w/ justification; invocation_id not flagged; baseline count pinned; ratchet PASSES on the routed tree; self-test green.
- 2026-06-16T13:20:22Z – claude:opus:reviewer-renata:reviewer – shell_pid=2008491 – Started review via action command
- 2026-06-16T13:22:46Z – user – shell_pid=2008491 – Review passed (supersedes cycle-1 which was a transient worktree_alloc_failed block, not a quality rejection — resolved via merge bdaa64531). AST short-id detector (substring, all 5 shapes incl str(raw_mission_id)[:8]) + failover-bypass rule; ratchet PASSES on routed tree with ONLY 2 justified doctor allow-list entries + 2 seam homes (no over-allow-listing — independent scan confirms 7 raw slices = 5 homes + 2 doctor tolerance, zero unaccounted consumers; baseline literal matches); invocation_id excluded by name predicate; negative-control non-trivial (exact-match regression proven to fail self-test); honesty note + deferred-class note present; ruff+mypy+C901 clean, no suppressions; only owned test file changed.
