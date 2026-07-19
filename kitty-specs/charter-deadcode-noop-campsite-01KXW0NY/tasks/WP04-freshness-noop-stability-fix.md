---
work_package_id: WP04
title: Preflight no-op-stability regression guard (#2373 already-remediated)
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-008
- NFR-001
tracker_refs:
- '#2373'
- '#1914'
planning_base_branch: feat/charter-deadcode-noop-campsite
merge_target_branch: feat/charter-deadcode-noop-campsite
branch_strategy: Planning artifacts for this mission were generated on feat/charter-deadcode-noop-campsite. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-deadcode-noop-campsite unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
history: []
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/charter_runtime/
create_intent:
- tests/specify_cli/charter_runtime/test_preflight_noop_stability.py
execution_mode: code_change
owned_files:
- tests/specify_cli/charter_runtime/test_preflight_noop_stability.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1567732"
shell_pid_created_at: "1784429244.93"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile via `/ad-hoc-profile-load python-pedro`
(implementer). Load the YAML — do not act on the persona name alone.

## Objective — GUARD ONLY (no behavioral change)

**⚠ Scope reversed by the post-tasks squad.** The #2373 residual no-op churn is **already fixed at
HEAD** — there is NO behavioral fix to make. Do NOT change `computer.py` or the synthesizer. This WP
adds a **preflight-level regression guard** that pins the already-correct no-op-stable behavior so it
cannot silently regress, and closes #2373 as verified-already-fixed.

**Why there is nothing to fix** (verified — see [`data-model.md` Post-tasks amendment](../data-model.md)):
- `synthesized_drg` freshness is a content-hash of `charter.yaml` **alone** (#2732, commit
  `4c5fb725c`) → a genuine no-op hashes equal → `fresh` → the preflight auto-refresh never invokes
  `charter synthesize`. There is no code path where an *unchanged* `charter.yaml` is judged stale.
- `write_pipeline.promote` guards all four written surfaces with `_substantively_equal` (#1912) →
  zero tracked-file diff even if synthesize ran.
- #2773 made `charter.yaml` the sole hash input; the render path writes only gitignored state.
- **Do NOT** re-home the freshness signal onto derived-catalog equality — that would OVER-SUPPRESS
  genuine `charter.yaml` staleness (INV-2/LM-5 violation). The whole-file hash IS the correct guard.

**Authoritative grounding**: [`contracts/no-op-stability.contract.md`](../contracts/no-op-stability.contract.md)
(G2, G3, G4), [`data-model.md` LM-1, LM-5, INV-2](../data-model.md).

## Context / grounding (verified at HEAD)

- `src/specify_cli/charter_runtime/preflight/runner.py:83 _PASS_STATES` = `{fresh, skipped,
  built_in_only}`; `_attempt_auto_refresh` (`:340`) only runs synthesize when `synthesized_drg` is
  stale, and aborts on a pre-dirty tree (`_detect_dirty_artifacts`, `:260`).
- `src/specify_cli/charter_runtime/freshness/computer.py:433-472` — the content-hash freshness.
- **Existing coverage** (cite, do not duplicate): `tests/specify_cli/charter_freshness/test_computer.py`
  (#2732 content-identity), `tests/architectural/test_no_op_stable_writes.py` (#1912 synthesize-twice).
  This WP adds only the **end-to-end preflight** assertion if it is genuinely missing.
- **LM-1 (masking):** this checkout's `.git/info/exclude` excludes `.kittify/doctrine/` +
  `.kittify/charter/provenance/`, and the repo is `built_in_only` (synthesis-manifest) — so it cannot
  reproduce anything. The guard fixture MUST fabricate a **real synthesized** doctrine-tracked state
  (a real `graph.yaml` + a manifest whose `bundle_content_hash` matches `charter.yaml`), committed
  clean, or the assertion is vacuous.

## Subtasks (guard-only)

### T012 — Preflight no-op-stability guard (G2/G3)
Create `tests/specify_cli/charter_runtime/test_preflight_noop_stability.py`. On a **real-synthesized,
doctrine-tracked, committed-clean** fixture, run `run_charter_preflight(auto_refresh=True)` **twice**
and assert: `git status --porcelain` is empty after each run, AND `charter synthesize` is not invoked
on the no-op (e.g. `synthesized_drg ∈ _PASS_STATES`). This SHOULD pass at HEAD — it pins the fix.
**If it fails, you found a real regression** — surface it; do not massage it green (a first-write
materialization of `??` untracked artifacts is NOT churn — see LM-1).

### T013 — INV-2 anti-over-suppression guard (G4/F3)
Assert a substantive `charter.yaml` edit still reports `synthesized_drg` **stale** → synthesize runs.
This guards against a future "fix" that over-suppresses genuine staleness (LM-5). If existing coverage
in `test_computer.py` already asserts exactly this at the preflight level, cite it and skip; otherwise
add it here.

### T014 — Verify
- `PWHEADLESS=1 pytest tests/specify_cli/charter_runtime/test_preflight_noop_stability.py -q` → green.
- Confirm NO change to `src/specify_cli/charter_runtime/**` or the synthesizer (guard-only).
- `ruff check` + `mypy --strict` on the new test → clean.

## Definition of Done
- A committed preflight-level guard proving no-op-stability (G2/G3) on a real-synthesized
  doctrine-tracked fixture, green at HEAD, plus an INV-2 guard (or a citation to existing equivalent).
  Zero production change. #2373 verdict evidence updated to verified-already-fixed + regression-guarded.

## Landmines
- **LM-1** fixture must be real-synthesized + doctrine-tracked (built_in_only/masked = vacuous).
- **LM-5** never introduce a signal change that over-suppresses genuine staleness.
- **No behavioral change** — if you feel the urge to edit `computer.py`, stop: demand a `git status`
  line showing a *tracked* file *modified* on a committed-clean tree first; it will not appear.

## Reviewer guidance
Verify the fixture is real-synthesized (not `built_in_only`, not masked); verify zero src change;
verify the INV-2 guard exists or is cited; reject any `computer.py`/synthesizer edit.

## Activity Log

- 2026-07-19T02:38:08Z – claude:sonnet:python-pedro:implementer – shell_pid=1510808 – Assigned agent via action command
- 2026-07-19T02:46:11Z – claude:sonnet:python-pedro:implementer – shell_pid=1510808 – guard-only, no src change, real-synthesized fixture, green at HEAD
- 2026-07-19T02:47:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=1567732 – Started review via action command
