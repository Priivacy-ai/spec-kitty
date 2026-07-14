---
work_package_id: WP02
title: Retire the runtime_bridge compat-delegate surface (critical path)
dependencies:
- WP01
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
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: docs/notes/runtime-bridge-delegate-classification.md
create_intent: []
execution_mode: planning_artifact
model: claude-sonnet-5
owned_files:
- docs/notes/runtime-bridge-delegate-classification.md
role: implementer
tags: []
shell_pid: "3200587"
shell_pid_created_at: "1783957774.75"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-003 + NFR-001 +
NFR-003, [plan.md](../plan.md) §IC-02 ("CRITICAL PATH"), and Scenario 2 in spec.md. **NFR-001 is binding:
this WP depends on WP01 — the dynamic-access-aware gate is what proves each deleted delegate is truly dead.
A deletion that lands before WP01 is a process violation.**

## Objective (RE-SEQUENCED → classification-only)

Grep-classify the ~416 `setattr(runtime_bridge…)` occurrences into forwarding-vs-real-seam and record the
45-candidate pure-forwarding table (repoint-then-delete / canonical-`__all__` / needs-call-site-refactor).
**The src-delegate DELETION moved to the new WP18** (post-repoint), because a delegate cannot be deleted
until WP03/WP04 repoint the test sites and the frozen `test_bridge_compat_surface.py` baseline is updated —
WP02 empirically proved 0-deletable-today (a reverted 5-name experiment reddened the frozen guard; 3 have
live production `_rb.<name>` deps). WP02 keeps the src files owned (it audited them) but makes **zero src
edits**; the deletion residue is WP18's. Keep the classification authoritative for WP03/WP04/WP18.

## Context

- The audit surface is **~416 `setattr(runtime_bridge…)` / `"runtime.next.runtime_bridge.<name>"`
  occurrences across 53 test files** (WP03 ~241 in `tests/next` + WP04 ~168)
  (`grep -rlE 'setattr\([^,]*runtime_bridge|runtime\.next\.runtime_bridge' tests/`).
  Not all are forwarding — classify FIRST. **WP02 records the classification only; the test-site repoint of
  those ~416 occurrences is WP03 (batch A) + WP04 (batch B), and the src-delegate DELETION is WP18.**
- Audited production files (`runtime_bridge.py` 108 KB + seam modules
  `runtime_bridge_{cores,io,identity,engine,composition,retrospective}.py`) are **owned by WP18** now; WP02
  makes zero src edits and owns only `docs/notes/runtime-bridge-delegate-classification.md`.
- NFR-003: **no production behaviour change** — WP02 is classification-only.

> **⚠ SUPERSEDED:** The T007/T008 "delete" guidance below is the pre-re-sequence text and is retained for
> history only. Under the re-sequence, WP02 performs **zero deletions** — deletion is WP18's. WP02's live
> subtasks are: T006 grep-classify, T007 record the 45-candidate table, T008 confirm 0-deletable-pre-repoint,
> T009 gate/suite green on unmodified src, T010 ruff/mypy clean + FR-016 tracer.

## Subtask guidance (pre-re-sequence — see SUPERSEDED banner above)

- **T006 — grep-classify first.** Enumerate every `setattr(runtime_bridge, <name>, …)` /
  `monkeypatch.setattr("runtime.next.runtime_bridge.<name>", …)` site and classify each `<name>` as
  **forwarding** (a pure re-export delegate → deletable) vs **real seam** (defined here, load-bearing →
  keep). Produce the classification as a short note in the WP's review evidence (Directive 003 — document
  the decision). Do NOT inline the #2560 strangler route-out.
- **T007 — delete pure re-export delegates in `runtime_bridge.py`.** Remove each forwarding delegate whose
  only body is `return <seam>.<name>(...)` / a module-level re-bind. Keep the 8 canonical `__all__` names
  (the public surface the seam modules and callers still resolve). Run the WP01 gate after each batch of
  deletions to prove the removed name is now dead.
- **T008 — seam-module re-exports.** If any of the seam modules (`runtime_bridge_*`) carry pure re-export
  forwarders of the same shape, delete those too; keep the real implementations.
- **T009 — prove + suite.** `.venv/bin/python -m pytest tests/architectural/test_no_dead_symbols.py -q`
  green (the dynamic-access-aware gate proves each deleted delegate dead) AND
  `.venv/bin/python -m pytest tests/runtime -q` green. NOTE: the monkeypatch-site repointing lands in
  WP03/WP04 — some `tests/next`/`tests/runtime` reds are EXPECTED here and are closed by those WPs; do not
  repoint test files in this WP (they are owned by WP03/WP04). Verify the production deletion is coherent
  (imports resolve, `__all__` intact); leave test-side repointing to the downstream WPs.
- **T010 — gates + tracer.** `ruff`/`mypy` clean on the diff. Record the NFR-001 dependency-on-WP01 in the
  review evidence. Append tracer rows.

## Branch Strategy

Branches from WP01's tip in the Lane-0 serial chain; merges into `feat/test-suite-friction-remediation`.
**Claim first after WP01** — this is the critical path; size for the full ~416-occurrence audit across 53
test files (WP03 ~241 in `tests/next` + WP04 ~168), while owning the src-delegate deletion only.

## Definition of Done (non-fakeable — NFR-002)

- [ ] Forwarding-vs-real-seam classification recorded for the ~416 occurrences across 53 test files (WP03
      ~241 in `tests/next` + WP04 ~168): the 45-candidate table (35 repoint-then-delete / 2 canonical
      `__all__` / 3 call-site-refactor) captured in review history + the FR-016 tracer.
- [ ] **Zero src deletions** — deletion deferred to WP18; the reverted 5-name experiment documented as proof
      no forwarder is deletable pre-repoint.
- [ ] Dead-code gate (`test_no_dead_symbols.py`, dynamic-access-aware from WP01) **green** on unmodified src.
- [ ] `tests/runtime` green (unmodified-source baseline); no `__all__`/import breakage.
- [ ] `ruff` + `mypy` clean (zero src diff); no production behaviour change (NFR-003).
- [ ] **Tracer (FR-016):** append rows to `../tracer-design-decisions.md` for the runtime_bridge parity
      suites this deletion observes (`tests/runtime/test_bridge_parity.py`, `tests/runtime/test_bridge_compat_surface.py`)
      + log friction to `../tracer-tooling-friction.md`.

## Risks

- **The critical-path pole.** A missed forwarding classification red-fails a sibling test in WP03/WP04.
  Classify exhaustively before deleting.
- **Deleting a real seam** — anything defined (not re-exported) in these modules stays. The WP01 gate is the
  arbiter: if deleting a name turns the gate red for a live caller, it was not a pure delegate.

## Reviewer guidance

- Confirm every deletion corresponds to a forwarding classification, and the 8 `__all__` names are intact.
- Confirm no test file was edited here (test repointing is WP03/WP04's owned surface).
- Confirm the deletion proof is the gate going green, not a manual grep.

## Activity Log

- 2026-07-13T15:04:35Z – claude:sonnet:python-pedro:implementer – shell_pid=3048275 – Assigned agent via action command
- 2026-07-13T15:43:27Z – claude – shell_pid=3048275 – T006 classification (Directive 003 evidence): audited all 45 pure-forwarding compat-surface candidates in runtime_bridge.py (37 native def/class 'Thin compat delegate' symbols + 8 plain self-alias re-export imports). RESULT: 0 safe to delete today. Grep across tests/ initially suggested 5 (_extract_wp_heading/_collect_requirement_refs_for_section/_iter_requirement_refs/_requirement_inline_refs_suffix/_is_requirement_heading) had zero monkeypatch/import references via the runtime_bridge path -- deleted them, ran scoped suite, and tests/runtime/test_bridge_cores.py::test_untracked_parse_helpers_are_identity_reexports RED (AttributeError), because it asserts getattr(rb,name) is getattr(cores,name) for that exact tuple, required by test_bridge_compat_surface.py's FROZEN exact-baseline assertion -- a dependency grep cannot see. Reverted (git checkout --). Confirmed baseline green after revert: tests/runtime/test_bridge_cores.py + test_bridge_compat_surface.py + tests/architectural/test_no_dead_symbols.py = 121 passed. Additionally 3 names (_retrospective_blocks_completion, _composition_dispatch_inputs, _has_generated_docs) have live PRODUCTION cross-seam _rb.<name> dependencies (runtime_bridge_engine.py, runtime_bridge_io.py) or bare in-module calls -- not deletable by test-repointing alone, need a call-site refactor too. 2 names (get_or_start_run, build_operational_context_for_claim) are the canonical __all__ surface -- permanently kept. CONCLUSION per lane-greenness mandate: defer ALL 45 to WP03 (repoint ~241 tests/next sites) + WP04 (repoint remaining ~168) -- both WPs to repoint-then-delete, not just repoint. T007/T008: zero deletions performed (none proven safe). T009: dead-symbols gate + tests/runtime baseline green (628 passed / 1 skipped on full tests/runtime, confirmed via scoped 121-test rerun after revert). T010: ruff+mypy clean (no src diff). No production files changed -- src/runtime/next/runtime_bridge.py reverted to committed HEAD after the failed 5-delegate experiment. Full 45-name classification table available on request.
- 2026-07-13T15:48:21Z – claude:sonnet:python-pedro:implementer – shell_pid=3048275 – Ready for review: T006 classification complete for all 45 pure-forwarding candidates; 0 safe deletions today (proven empirically via a reverted 5-name experiment that broke a frozen compat-surface test); deferred to WP03/WP04 (repoint-then-delete). See add-history evidence. Gates green, no src diff.
- 2026-07-13T15:49:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=3200587 – Started review via action command
- 2026-07-13T16:01:09Z – user – shell_pid=3200587 – ARBITER (reviewer stalled): WP02's 0-delete/45-defer is the CORRECT call — deleting any delegate reds the frozen test_bridge_compat_surface baseline and/or a live patcher; 3 have live production _rb deps. Classification sound + documented. RE-SCOPE: WP03/WP04 do repoint-THEN-delete + update the frozen compat baseline + refactor the 3 production call-sites.
