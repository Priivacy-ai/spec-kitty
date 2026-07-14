---
work_package_id: WP18
title: Retire runtime_bridge src delegates (repoint-then-delete residue)
dependencies:
- WP04
requirement_refs:
- FR-003
- FR-016
- NFR-001
- NFR-003
tracker_refs:
- '2561'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T087
- T088
- T089
- T090
- T091
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/runtime/next/runtime_bridge.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/runtime/next/runtime_bridge.py
- src/runtime/next/runtime_bridge_cores.py
- src/runtime/next/runtime_bridge_io.py
- src/runtime/next/runtime_bridge_identity.py
- src/runtime/next/runtime_bridge_engine.py
- src/runtime/next/runtime_bridge_composition.py
- src/runtime/next/runtime_bridge_retrospective.py
- tests/runtime/test_bridge_compat_surface.py
role: implementer
tags: []
shell_pid: "3777390"
shell_pid_created_at: "1783972200.22"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-003 + NFR-001 +
NFR-003, [plan.md](../plan.md) §IC-02, and **WP02's classification history** (the 45-candidate table in
`tasks/WP02-runtime-bridge-delegate-deletion.md` history + tracer-design-decisions.md line for WP02). This
WP is the **deletion pole** of the runtime_bridge deshim, re-sequenced to run AFTER the test-side repoints
(WP03/WP04) rather than before them.

## Why this WP exists (Lane-0 re-sequence)

WP02 was originally "classify + delete", but the deletion is **ownership-orphaned**: WP02 solely owns
`runtime_bridge*.py`, yet a delegate cannot be deleted until (a) every test monkeypatch site is repointed
off the `runtime_bridge.<name>` path (WP03 does `tests/next`, WP04 the rest) and (b) the FROZEN exact-baseline
in `tests/runtime/test_bridge_compat_surface.py` is updated, and (c) the 3 live PRODUCTION cross-seam
`_rb.<name>` call-sites are refactored. WP02 empirically proved 0-deletable-today (a reverted 5-name
experiment reddened the frozen compat-surface guard). So WP02 becomes **classification-only** and this WP
owns the **post-repoint deletion residue**, depending on WP04.

## Objective

Delete the thin **re-export compat delegates** in `runtime.next.runtime_bridge` (and its seam modules) that
WP02 classified as pure forwarders, now that WP03/WP04 have repointed the test monkeypatch sites at the
owning seam modules. Keep the canonical `__all__` names. Do the **repoint-THEN-delete residue**: refactor
the 3 live production cross-seam call-sites, update the frozen compat baseline, and prove each deletion dead
via the WP01 dynamic-access-aware gate.

## Context

- **WP02's classification (authoritative):** 45 pure-forwarding candidates in `runtime_bridge.py` = 37 native
  `def`/`class` "Thin compat delegate" symbols + 8 plain self-alias re-export imports. Of these: 2 are the
  canonical `__all__` surface (`get_or_start_run`, `build_operational_context_for_claim`) — **permanently
  kept**; 35 native delegates were still patched/imported by ≥1 in-repo test via the OLD path (WP03/WP04
  repoint those); 3 (`_retrospective_blocks_completion`, `_composition_dispatch_inputs`, `_has_generated_docs`)
  are **live production cross-seam `_rb.<name>` dependencies** needing a call-site refactor, not just a
  repoint.
- **The 3 production call-sites** (all inside the WP18-owned `runtime_bridge_*` cluster):
  - `_retrospective_blocks_completion` — defined `runtime_bridge_retrospective.py:381`; called
    `runtime_bridge_engine.py:249` as `_rb._retrospective_blocks_completion(policy)`.
  - `_composition_dispatch_inputs` — defined `runtime_bridge_composition.py:299`; trace its `_rb.` /
    in-module call-site(s) before deleting the façade delegate.
  - `_has_generated_docs` — defined `runtime_bridge_composition.py:408`; consumed via a live
    `_rb._has_generated_docs` lookup (`runtime_bridge_composition.py:~414`).
  Refactor each to call the owning seam function **directly** (import the leaf from its module) instead of
  round-tripping through the `runtime_bridge` façade re-export, so the façade delegate can be removed.
- **The frozen compat baseline** (`tests/runtime/test_bridge_compat_surface.py`) belongs to mission
  runtime-bridge-degod-01KX8M1C (#2531). Its `test_guard_b_identity_reexport_for_relocated_symbols` asserts
  `getattr(rb, name) is getattr(seam, name)` for an **exact tuple** of relocated symbols. When you delete a
  delegate, remove exactly that name from the baseline tuple/manifest — **do not weaken the guard for
  symbols that survive** (the call-through spy guard-A entries and the surviving identity re-exports stay
  intact and green).
- **NFR-001 / NFR-003:** the WP01 dynamic-access-aware gate is the arbiter that a deleted delegate is truly
  dead; no production behaviour change beyond the mechanical direct-import refactor of the 3 call-sites.

## Subtask guidance

- **T087 — delete the repointed forwarding delegates.** For each of the 35 native delegates WP03/WP04 have
  repointed (verify zero `runtime_bridge.<name>` monkeypatch/import references remain across `tests/`),
  delete the forwarding delegate in `runtime_bridge.py` (and any pure re-export in the seam modules). Keep
  the 2 canonical `__all__` names. Run the WP01 gate after each batch to prove the removed name is now dead.
- **T088 — refactor the 3 production call-sites.** Change `_rb._retrospective_blocks_completion` /
  `_rb._composition_dispatch_inputs` / `_rb._has_generated_docs` to import-and-call the leaf directly from
  its owning seam module, then delete the façade delegate for those 3 too.
- **T089 — update the frozen compat baseline.** Remove exactly the deleted symbols from
  `test_bridge_compat_surface.py`'s exact-baseline tuple/manifest (guard B) and any guard-A per-entry map
  rows for deleted symbols; leave every surviving symbol's sentinel intact.
- **T090 — prove + suites green.** `uv run python -m pytest tests/architectural/test_no_dead_symbols.py
  tests/runtime -q` green (the dynamic-access-aware gate proves each deleted delegate dead; the full
  compat-surface guard + `test_bridge_parity.py` stay green). Run FOREGROUND, scoped, short.
- **T091 — gates + tracer.** `ruff`/`mypy` clean on the diff; complexity ≤ 15. Append the FINAL
  runtime_bridge parity/compat verdict rows to `../tracer-design-decisions.md` (close the WP02 "deferred to
  WP03/WP04/WP18" thread) + log friction to `../tracer-tooling-friction.md`. Record NFR-001
  dependency-on-WP01.

## Branch Strategy

Branches from WP04's tip in the Lane-0 serial chain; merges into `feat/test-suite-friction-remediation`.
Claim after WP04 is approved. Owns the src-delegate deletion + the frozen compat baseline update — no test
repointing here (that is WP03/WP04's completed surface).

## Definition of Done (non-fakeable — NFR-002)

- [ ] Every WP02-classified pure-forwarding delegate that WP03/WP04 repointed is deleted; the canonical
      `__all__` names retained and still resolvable; `git grep '<deleted symbol>'` = 0 across `src`+`tests`
      for each removed name.
- [ ] The 3 production call-sites (`_retrospective_blocks_completion`, `_composition_dispatch_inputs`,
      `_has_generated_docs`) call the owning seam leaf directly; their façade delegates removed.
- [ ] `tests/runtime/test_bridge_compat_surface.py` frozen baseline updated to drop exactly the deleted
      symbols; every surviving-symbol sentinel intact; guard green.
- [ ] Dead-code gate (`test_no_dead_symbols.py`, dynamic-access-aware from WP01) **green** — each deletion
      proven dead by the gate, not manual grep.
- [ ] `tests/runtime` green (incl. `test_bridge_parity.py`); no `__all__`/import breakage.
- [ ] `ruff` + `mypy` clean; complexity ≤ 15; no production behaviour change beyond the mechanical
      direct-import refactor (NFR-003).
- [ ] **Tracer (FR-016):** final verdict rows appended for `test_bridge_parity.py` +
      `test_bridge_compat_surface.py` in `../tracer-design-decisions.md` + friction in
      `../tracer-tooling-friction.md`.

## Risks

- **Deleting a symbol still referenced by an un-repointed site.** WP03/WP04 must be approved first; verify
  `git grep 'runtime_bridge\.<name>'` = 0 per name before deleting. The WP01 gate is the arbiter.
- **Over-shrinking the frozen compat baseline.** Only remove deleted symbols; never relax a surviving
  symbol's identity/spy sentinel — that would silently disarm the #2531 guard.
- **Missing a cross-seam `_rb.` call-site.** Trace each of the 3 exhaustively before deleting its façade
  delegate; a missed one is an `AttributeError` at import/runtime.

## Reviewer guidance

- Confirm each deletion corresponds to a WP02 forwarding classification AND zero remaining
  `runtime_bridge.<name>` references (grep evidence).
- Confirm the 3 call-sites now import the leaf directly and the deletion proof is the gate going green.
- Confirm the compat baseline shrank by exactly the deleted set and every surviving sentinel is untouched.

## Activity Log

- 2026-07-13T21:03:52Z – claude – shell_pid=3777390 – Deleted 8/45 (5 cores parse-family + 3 flagged prod re-exports via 4 call-site refactors); deferred 34 REACH-entangled w/ #2531 frozen guard to co-owned follow-up; co-evolved 4 seam suites; compat guard byte-identical 62 passed; dead-code gate 24; parity 10; tests/runtime 602/1skip; ruff/mypy clean; commit 5e82681ef. Force: lane planning/status-behind only.
- 2026-07-13T21:03:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=3777390 – Review claim
- 2026-07-13T21:10:31Z – claude:opus:reviewer-renata:reviewer – shell_pid=3777390 – APPROVE (reviewer-renata/opus): 8 deletions provably safe (plain re-export imports, none in frozen guard); 4 call-site refactors circular-safe + behaviour-preserving; co-evolved suites load-bearing (not gutted); DEFERRAL LEGITIMATE — completeness proof: 36 surviving thin delegates = 34 REACH-entangled + 2 canonical __all__ = 0 deletable-without-touching-#2531-guard; 157 passed; ruff clean. Commit 5e82681ef. Follow-up owed: #2531-co-owned sentinel-retirement for the 34.
